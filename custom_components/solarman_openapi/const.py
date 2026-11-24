"""Constants for the SOLARMAN OpenAPI integration."""

DOMAIN = "solarman_openapi"

CONF_APP_ID = "app_id"
CONF_APP_SECRET = "app_secret"
CONF_REGION = "region"
CONF_EMAIL = "email"
CONF_PASSWORD_HASH = "password_hash"
CONF_LOGGER_SN = "logger_sn"
CONF_ORG_ID = "org_id"

# Form-only fields
CONF_INVERTER_SNS = "inverter_sns"  # manual list, comma/space separated
CONF_SELECTED = "selected_inverters"

# Options
CONF_SCAN_INTERVAL = "scan_interval"
CONF_INVERTERS = "inverters"  # {inverter_sn: participation_percent}
CONF_POWER_KEY = "power_key"
CONF_DAILY_KEY = "daily_energy_key"
CONF_TOTAL_KEY = "total_energy_key"

REGIONS = {
    "global": "https://globalapi.solarmanpv.com",
    "china": "https://api.solarmanpv.com",
}
DEFAULT_REGION = "global"
DEFAULT_SCAN_INTERVAL = 5  # minutes
MIN_SCAN_INTERVAL = 1
DEFAULT_SHARE = 100.0

# Aggregate ("participation") sensors. Data keys differ between inverter models,
# so we try these in order unless the user picks one in the options.
KIND_POWER = "power"
KIND_DAILY = "daily_energy"
KIND_TOTAL = "total_energy"

OPTION_FOR_KIND = {
    KIND_POWER: CONF_POWER_KEY,
    KIND_DAILY: CONF_DAILY_KEY,
    KIND_TOTAL: CONF_TOTAL_KEY,
}
DEFAULT_KEYS = {
    KIND_POWER: ["APo_t1", "Pac1", "P_AC", "Pac", "TPG"],
    KIND_DAILY: ["Etdy_ge1", "Etdy_ge0", "E_Today", "Etdy_pv1"],
    KIND_TOTAL: ["Et_ge0", "Et_ge1", "E_Total", "Et_pv1"],
}
