import pyotp

# --- Credential Source ---
# Set to True to pull credentials from 1Password, False to use manual values below
USE_1PASSWORD = False

# --- 1Password Settings (only used if USE_1PASSWORD = True) ---
OP_SERVICE_ACCOUNT_TOKEN = ""
OP_EMPLOYEE_ID_REF = "op://YourVault/Target/username"
OP_PASSWORD_REF = "op://YourVault/Target/password"
OP_TOTP_SECRET_REF = "op://YourVault/Target/TOTP_secret"

# --- Manual Credentials (only used if USE_1PASSWORD = False) ---
MANUAL_EMPLOYEE_ID = ""
MANUAL_PASSWORD = ""
MANUAL_TOTP_SECRET = ""

# --- General Settings ---
STORE_NUMBER = ""
API_KEY = "d4465835234778cb3c58aeded4b489b306841a9f"
PUSHOVER_APP_API_KEY = ""
PUSHOVER_USER_API_KEY = ""
run_posted_shifts = True
headless = True

# --- Load Credentials ---
if USE_1PASSWORD:
    from onepassword_helper import load_credentials
    EMPLOYEE_ID, PASSWORD, _TOTP_SECRET = load_credentials(
        OP_SERVICE_ACCOUNT_TOKEN,
        [OP_EMPLOYEE_ID_REF, OP_PASSWORD_REF, OP_TOTP_SECRET_REF],
    )
else:
    EMPLOYEE_ID = MANUAL_EMPLOYEE_ID
    PASSWORD = MANUAL_PASSWORD
    _TOTP_SECRET = MANUAL_TOTP_SECRET

if _TOTP_SECRET.startswith("otpauth://"):
    totp = pyotp.parse_uri(_TOTP_SECRET)
else:
    totp = pyotp.TOTP(_TOTP_SECRET)



def get_mfa_code():
    return totp.now()
