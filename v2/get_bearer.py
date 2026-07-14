#!/opt/scripts/myGoogleCalendar/v2/.venv/bin/python

def get_token():
    import json
    import time
    import config_file
    from loguru import logger
    import undetected_chromedriver as uc
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.chrome.service import Service

    logger.info("Setting up Chrome Options")
    # Chrome Options
    options = uc.ChromeOptions()
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    options.add_experimental_option("perfLoggingPrefs", {"enableNetwork": True})
    service = Service()
    options.add_argument("--incognito")
    options.headless = config_file.headless
    # NEEDED FOR HEADLESS
    options.add_argument("--enable-automation")
    # Needed for Linux VM Headless
    options.add_argument("--disable-gpu")
    # Needed for Linux VM.
    options.add_argument("--disable-software-rasterizer")

    # options.add_argument("--no-sandbox")
    # options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--incognito")
    # options.add_argument("--disable-extensions")
    # options.add_argument("--disable-browser-side-navigation")
    # options.add_argument("--disable-web-security")
    # options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--disable-infobars")
    # options.add_argument("--disable-setuid-sandbox")

    # Detect Chrome version to avoid ChromeDriver version mismatch
    import subprocess
    import re
    version_main = None
    try:
        chrome_version_out = subprocess.check_output(["google-chrome", "--version"]).decode("utf-8")
        match = re.search(r"Google Chrome (\d+)", chrome_version_out)
        if match:
            version_main = int(match.group(1))
            logger.info(f"Detected Chrome major version: {version_main}")
    except Exception as e:
        logger.warning(f"Could not automatically detect Chrome version: {e}")

    browser = uc.Chrome(use_subprocess=True, options=options, service=service, version_main=version_main)
    logger.success("ChromeDriver Setup! Starting")

    # navigate to a website
    logger.info("Launching myTime")
    browser.get("http://mytime.target.com")
    try:
        element_present = ec.presence_of_element_located((By.ID, "loginID"))
        WebDriverWait(browser, 10).until(element_present)
        time.sleep(1)
    except TimeoutException:
        logger.error("Timed out waiting for Login Page to load")
        browser.close()

    logger.info("entering username and password...")
    username = browser.find_element(By.ID, "loginID")
    password = browser.find_element(By.ID, "password")
    # This finds the login and the password box
    logger.info("Entering Username")
    username.click()
    username.clear()
    username.send_keys(config_file.EMPLOYEE_ID)

    logger.info("Entering Password")
    password.click()
    password.clear()
    password.send_keys(config_file.PASSWORD)

    logger.info("Pressing Submit")
    login_button = browser.find_element(By.ID, "submit-button")
    login_button.click()

    logger.info("Waiting for MFA selection page...")
    try:
        mfa_xpath = '//*[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "authenticator")]'
        element_present = ec.element_to_be_clickable((By.XPATH, mfa_xpath))
        mfa_button = WebDriverWait(browser, 15).until(element_present)
        mfa_button.click()
        logger.success("Clicked MFA Authenticator button")
    except TimeoutException:
        screenshot_path = "mfa_timeout.png"
        html_path = "mfa_timeout.html"
        browser.save_screenshot(screenshot_path)
        with open(html_path, "w") as f:
            f.write(browser.page_source)
        logger.error(f"Timed out waiting for Authenticator button. Saved screenshot to {screenshot_path} and HTML to {html_path}")
        raise

    try:
        element_present = ec.presence_of_element_located((By.ID, "totp-code"))
        WebDriverWait(browser, 10).until(element_present)
        time.sleep(1)
    except TimeoutException:
        logger.error("Timed out OTP button to load")
        browser.close()

    logger.success("Account Valid! Logging into 2FA")
    otp = browser.find_element(By.ID, "totp-code")
    otp.click()
    otp.send_keys(config_file.get_mfa_code())

    browser.find_element(By.ID, "submit-button").click()
    logger.info("Clicking submit...")
    
    # Dynamically wait for the dashboard page to load or password change prompt to appear
    logger.info("Waiting for dashboard to load...")
    try:
        WebDriverWait(browser, 30).until(
            lambda driver: "team-member/home" in driver.current_url or 
                           any(txt in driver.page_source for txt in ["Welcome", "Next Shift", "Home"]) or
                           "laptop" in driver.page_source.lower()
        )
        logger.success("Dashboard page loaded!")
    except TimeoutException:
        logger.warning("Timed out waiting for dashboard. Checking page source anyway...")

    # Check if password change is required
    time.sleep(2)
    if "laptop" in browser.page_source.lower():
        logger.warning("Password change required detected.")
        from db import get_setting, set_setting
        from functions import notify_user
        import datetime
        today = str(datetime.date.today())
        last_notified = get_setting("last_password_change_notification")
        if last_notified != today:
            notify_user("Target SSO is requesting a password change.")
            set_setting("last_password_change_notification", today)

    logger.success("Logged in successfully! Grabbing Bearer token")
    logs = browser.get_log("performance")
    for entry in logs:
        if "Bearer " in str(entry["message"]):
            json_message_data = json.loads(str(entry["message"]))

            # Try to extract Bearer token from request headers (case-insensitive key match)
            try:
                if "request" in json_message_data["message"]["params"]:
                    request_headers = json_message_data["message"]["params"]["request"].get("headers", {})
                    auth_key = next((k for k in request_headers if k.lower() == "authorization"), None)
                    if auth_key:
                        authorization_json = request_headers[auth_key]
                        if "Bearer " in authorization_json:
                            logger.success("Bearer obtained from request headers! Closing...")
                            browser.close()
                            return authorization_json
            except (KeyError, TypeError):
                pass

            # Try to extract Bearer token from response headers (case-insensitive key match)
            try:
                if "response" in json_message_data["message"]["params"]:
                    response_headers = json_message_data["message"]["params"]["response"].get("headers", {})
                    auth_key = next((k for k in response_headers if k.lower() == "authorization"), None)
                    if auth_key:
                        authorization_json = response_headers[auth_key]
                        if "Bearer " in authorization_json:
                            logger.success("Bearer obtained from response headers! Closing...")
                            browser.close()
                            return authorization_json
            except (KeyError, TypeError):
                pass

    # If we get here, we didn't find the Bearer token
    logger.error("Failed to extract Bearer token from logs")
    browser.close()
    raise Exception("Could not find Bearer token in browser logs")

