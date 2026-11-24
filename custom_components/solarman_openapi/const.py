"""Constants for the SOLARMAN OpenAPI integration."""

DOMAIN = "solarman_openapi"

CONF_APP_ID = "app_id"
CONF_APP_SECRET = "app_secret"
CONF_REGION = "region"
CONF_EMAIL = "email"
CONF_PASSWORD_HASH = "password_hash"
CONF_DEVICE_SN = "device_sn"
CONF_ORG_ID = "org_id"
CONF_SCAN_INTERVAL = "scan_interval"

REGIONS = {
    "global": "https://globalapi.solarmanpv.com",
    "china": "https://api.solarmanpv.com",
}
DEFAULT_REGION = "global"
DEFAULT_SCAN_INTERVAL = 5  # minutes
MIN_SCAN_INTERVAL = 1
