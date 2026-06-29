#!/opt/scripts/myGoogleCalendar/v2/.venv/bin/python

import get_schedule
import get_posted_shifts
import config_file

if config_file.run_posted_shifts:
    get_posted_shifts.get_posted_shifts()
get_schedule.start_get_schedule()
