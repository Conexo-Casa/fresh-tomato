"""Constants for the FreshTomato integration."""

DOMAIN = "freshtomato"
MANUFACTURER = "FreshTomato"

# Config entry keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_HTTP_ID = "http_id"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_PORT = 80
DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_VERIFY_SSL = False

# FreshTomato HTTP API paths
ENDPOINT_UPDATE = "/update.cgi"
ENDPOINT_STATUS = "/status-data.jsx"

# update.cgi exec parameters
EXEC_NETDEV = "netdev"
EXEC_WLDEV = "wldev"

# Coordinator keys
DATA_ROUTER = "router"
DATA_DEVICES = "devices"

# Sensor unique ID prefixes
SENSOR_PREFIX = f"{DOMAIN}_"
