#!/opt/scripts/myGoogleCalendar/v2/.venv/bin/python

import os
import datetime
import requests
from dataclasses import dataclass
from fake_useragent import UserAgent
from sqlalchemy import select
from sqlalchemy.orm import Session

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from loguru import logger

import config_file
from db import engine, SeenShift, get_setting, set_setting

logger.add("script.log", rotation="500 MB")
logger.info("Changing cwd to file path")
os.chdir(os.path.dirname(__file__))

logger.info("Initializing Google Calendar... Please Wait.")

creds = None
SCOPES = ["https://www.googleapis.com/auth/calendar"]

if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
    with open("token.json", "w") as token:
        token.write(creds.to_json())
service = build("calendar", "v3", credentials=creds)


@dataclass
class Store:
    address: str = ""
    timezone: str = ""
    store_id: str = "0000"


def get_schedule_headers():
    ua = UserAgent()
    return {
        "User-Agent": ua.random,
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
    }


def get_auth_headers(bearer_token):
    return {"Authorization": bearer_token}


def get_posted_shifts_headers(bearer_token):
    return {
        "Authorization": bearer_token,
        "Page-Origin": "AVAILABLE_SHIFTS",
    }


def _notify_login_failure(message):
    """Send a login failure notification at most once per day."""
    today = str(datetime.date.today())
    last_notified = get_setting("last_login_failure_notification")
    if last_notified == today:
        logger.info("Login failure notification already sent today, skipping.")
        return
    notify_user(message)
    set_setting("last_login_failure_notification", today)


def validate_and_refresh_token():
    """Read bearer token from db, validate it, refresh if needed. Returns (auth_headers, posted_shift_headers)."""
    import get_bearer

    bearer = get_setting("bearer")
    auth_headers = get_auth_headers(bearer)
    posted_headers = get_posted_shifts_headers(bearer)

    logger.info("Testing previously used token.")
    if test_token(auth_headers).status_code == 401:
        logger.warning("Token invalid. Generating new token...")
        try:
            new_token = get_bearer.get_token()
        except Exception as e:
            logger.error(f"Failed to obtain new token: {e}")
            _notify_login_failure(f"Login failed: {e}")
            exit(-1)
        logger.success("New Token obtained. Testing new token...")
        auth_headers = get_auth_headers(new_token)
        posted_headers = get_posted_shifts_headers(new_token)
        if test_token(auth_headers).status_code == 400:
            logger.success("New Token valid! Saving to database...")
            set_setting("bearer", new_token)
        else:
            logger.error(f"New Token invalid! Status: {test_token(auth_headers).status_code}")
            _notify_login_failure("Login failed: new bearer token was invalid after SSO login.")
            exit(-1)
    else:
        logger.success("Existing Token valid!")

    return auth_headers, posted_headers


def get_week_ranges(num_weeks=4):
    """Yield (start_date, end_date) tuples for num_weeks consecutive weeks starting from the current week."""
    start = datetime.datetime.now()
    start -= datetime.timedelta(start.weekday() + 1)
    end = start + datetime.timedelta(6)

    for i in range(num_weeks):
        if i > 0:
            start += datetime.timedelta(7)
            end += datetime.timedelta(7)
        yield start.date(), end.date()


def check_api_response(response, context):
    """Check API response status and exit with error details if not 200."""
    if response.status_code != 200:
        logger.error(f"{context} - Status: {response.status_code}")
        logger.error(f"Response text: {response.text}")
        try:
            logger.error(f"Response JSON: {response.json()}")
        except (ValueError, KeyError):
            pass
        exit(-2)


def notify_user(message):
    if config_file.PUSHOVER_APP_API_KEY == "" or config_file.PUSHOVER_USER_API_KEY == "":
        logger.info("Config file for pushover is empty, ignoring")
        return
    logger.info("Notifying User via Pushover...")
    r = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": config_file.PUSHOVER_APP_API_KEY,
            "user": config_file.PUSHOVER_USER_API_KEY,
            "message": message,
        },
    )
    try:
        r.raise_for_status()
        logger.success("User Notified")
    except requests.HTTPError:
        logger.error(f"Notifying FAILED {r.text}")



def create_event(location, job_title, s_time, e_time):
    event = {
        "summary": "Target",
        "location": location,
        "description": f"You are being requested to work a shift of {job_title}",
        "colorId": 11,
        "start": {"dateTime": s_time},
        "end": {"dateTime": e_time},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 45}],
        },
    }
    event = service.events().insert(calendarId="primary", body=event).execute()
    logger.success("Event created: %s" % (event.get("htmlLink")))


def get_timezone_offset(iana_timezone, target_date=None):
    """Get the UTC offset for a given date and IANA timezone, correctly accounting for DST."""
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(iana_timezone)
    if target_date is None:
        target_date = datetime.date.today()
    dt = datetime.datetime(target_date.year, target_date.month, target_date.day, 12, tzinfo=tz)
    total_seconds = int(dt.utcoffset().total_seconds())
    hours, remainder = divmod(abs(total_seconds), 3600)
    minutes = remainder // 60
    sign = "+" if total_seconds >= 0 else "-"
    return f"{sign}{hours:02d}:{minutes:02d}"


KNOWN_STORES = {
    "1964": {
        "address": "1275 Caroline St NE, Atlanta, GA 30307",
        "timezone": "America/New_York"
    }
}


def get_store_info(store_id):
    s = Store()
    s.store_id = store_id
    
    # Default/fallback values
    s.address = "Unknown Address"
    s.timezone = "America/New_York"

    if store_id in KNOWN_STORES:
        s.address = KNOWN_STORES[store_id]["address"]
        s.timezone = KNOWN_STORES[store_id]["timezone"]
        logger.info(f"Using known store info for {store_id} (timezone: {s.timezone})")
        return s

    logger.info(f"Attempting to fetch store info for {store_id} from API...")
    try:
        r = requests.get(
            "https://redsky.target.com/redsky_aggregations/v1/web/store_location_v1"
            f"?store_id={store_id}"
            f"&key={config_file.API_KEY}",
            headers=get_schedule_headers(),
            timeout=5
        )
        if r.status_code == 200:
            store_data = r.json()["data"]["store"]
            store_json = store_data["mailing_address"]
            s.address = (
                f"{store_json['address_line1']} {store_json['city']}, "
                f"{store_json['region']}, {store_json['postal_code']}"
            )
            s.timezone = store_data["geographic_specifications"]["iso_time_zone_code"]
            logger.info(f"Successfully fetched store {store_id} timezone: {s.timezone}")
        else:
            logger.warning(
                f"Failed to fetch store info for {store_id} from API (status {r.status_code}). "
                f"Using default timezone: {s.timezone}"
            )
    except Exception as e:
        logger.warning(
            f"Error fetching store info for {store_id}: {e}. "
            f"Using default timezone: {s.timezone}"
        )
        
    return s


def call_wfm(hdr, start_date, end_date):
    url = (
        f"https://api.target.com/wfm_schedules/v1/weekly_schedules?"
        f"team_member_number=00{config_file.EMPLOYEE_ID}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        f"&location_id="
        f"&key={config_file.API_KEY}"
    )
    logger.info(f"Calling WFM API: {url}")
    r = requests.get(url, headers=hdr)
    logger.info(f"WFM API response status: {r.status_code}")
    return r


def call_available_shifts(hdr, start_date, end_date):
    url = (
        f"https://api.target.com/wfm_available_shifts/v1/available_shifts?"
        f"worker_id={config_file.EMPLOYEE_ID}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        f"&location_ids={config_file.STORE_NUMBER}"
        f"&key={config_file.API_KEY}"
    )
    logger.info(f"Calling Available Shifts API: {url}")
    r = requests.get(url, headers=hdr)
    logger.info(f"Available Shifts API response status: {r.status_code}")
    return r


def test_token(test_header):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=today.weekday())
    end = start + datetime.timedelta(days=6)
    test_request = requests.get(
        f"https://api.target.com/wfm_schedules/v1/weekly_schedules?"
        f"team_member_number=00{config_file.EMPLOYEE_ID}"
        f"&start_date={start}"
        f"&end_date={end}"
        f"&location_id="
        f"&key={config_file.API_KEY}",
        headers=test_header,
    )
    return test_request


def seen_or_record(shift):
    with Session(engine) as session:
        logger.info(f"Checking if shift {shift['available_shift_id']} exists")
        result = session.scalar(
            select(SeenShift).filter(SeenShift.id == shift["available_shift_id"])
        )

        if result:
            logger.info("Shift found, exiting function")
            return
        logger.info("Shift not found, adding to database")
        new_shift = SeenShift(id=shift["available_shift_id"])
        session.add(new_shift)
        session.commit()

        dt_start = datetime.datetime.fromisoformat(shift["shift_start"])
        dt_end = datetime.datetime.fromisoformat(shift["shift_end"])

        notify_user(
            f"A new {shift['shift_hours']} hour shift has been posted for {dt_start.date()} "
            f"from {dt_start.strftime('%I:%M %p')} "
            f"to {dt_end.strftime('%I:%M %p')} for "
            f"{shift['org_structure']['job']}"
        )
