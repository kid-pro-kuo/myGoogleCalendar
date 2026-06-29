#!/opt/scripts/myGoogleCalendar/v2/.venv/bin/python

import functions
from loguru import logger


def get_posted_shifts():
    logger.info("Starting get_posted_shifts function.")
    _, posted_shift_headers = functions.validate_and_refresh_token()

    logger.info("Starting API calls for available shifts.")
    for start_date, end_date in functions.get_week_ranges():
        logger.info(f"Fetching available shifts for {start_date} to {end_date}")
        call = functions.call_available_shifts(posted_shift_headers, start_date, end_date)
        functions.check_api_response(call, f"Available Shifts API error for {start_date} to {end_date}")
        call_json = call.json()

        if not call_json["available_shifts"]:
            logger.info("No available shifts found.")
            continue
        logger.success("Shifts found!")

        for shift in call_json["available_shifts"]:
            functions.seen_or_record(shift)
