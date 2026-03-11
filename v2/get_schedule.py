import functions
from loguru import logger


def start_get_schedule():
    logger.info("Starting start_get_schedule function.")
    store_info = functions.Store()
    auth_headers, _ = functions.validate_and_refresh_token()

    for start_date, end_date in functions.get_week_ranges():
        logger.info(f"Fetching schedule for {start_date} to {end_date}")
        call = functions.call_wfm(auth_headers, start_date, end_date)
        functions.check_api_response(call, f"WFM Schedule API error for {start_date} to {end_date}")
        call_json = call.json()

        for j in range(7):
            schedule = call_json["schedules"][j]
            if schedule["total_display_segments"] == 0:
                logger.info(f'No shifts found for {schedule["schedule_date"]}')
                continue

            segment = schedule["display_segments"][0]
            shift_location = segment["location"]
            if store_info.store_id != shift_location:
                logger.warning(
                    f"Current location {store_info.store_id} incorrect. "
                    f"Retrieving store location for {shift_location}"
                )
                store_info = functions.get_store_info(shift_location)

            job_title = segment["job_name"]
            if segment["total_jobs"] > 1:
                logger.info("Multiple shifts found. Grabbing all of them")
                for k in range(1, segment["total_jobs"]):
                    temp = segment["jobs"][k]["job_path"]
                    job_title = f'{job_title} and {temp.split("/")[-1]}'
            logger.success(f"Shifts found! {job_title}")

            shift_start = f"{segment['segment_start'][:10]}T{segment['segment_start'][-8:]}{store_info.timezone_offset}"
            shift_end = f"{segment['segment_end'][:10]}T{segment['segment_end'][-8:]}{store_info.timezone_offset}"
            full_date = schedule["schedule_date"]
            description = f"You are being requested to work a shift of {job_title}"

            search_start = f"{full_date}T00:00:00{store_info.timezone_offset}"
            search_end = f"{full_date}T23:59:00{store_info.timezone_offset}"
            events_result = (
                functions.service.events()
                .list(
                    calendarId="primary",
                    timeMin=search_start,
                    timeMax=search_end,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            make_event = True
            for event in events:
                if event.get("summary") != "Target":
                    continue
                if (
                    event["start"]["dateTime"] == shift_start
                    and event["end"]["dateTime"] == shift_end
                    and event.get("description") == description
                ):
                    logger.info("Existing shift found in GCal. Ignoring....")
                    make_event = False
                    break
                else:
                    logger.warning("Existing item found but with differences... Updating...")
                    functions.notify_user(f"Shift Modification on {full_date} for {job_title}")
                    event["description"] = description
                    event["start"]["dateTime"] = shift_start
                    event["end"]["dateTime"] = shift_end
                    functions.service.events().update(
                        calendarId="primary", eventId=event["id"], body=event
                    ).execute()
                    make_event = False
                    break

            if make_event:
                functions.create_event(store_info.address, job_title, shift_start, shift_end)
                functions.notify_user(f"New shift posted on {full_date} for {job_title}")

    logger.success("Script Complete, Exiting Gracefully...")
