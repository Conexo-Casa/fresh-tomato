"""Constants for the FreshTomato integration."""

DOMAIN = "freshtomato"
DEFAULT_NAME = "FreshTomato Router"
DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 30  # seconds

CONF_HTTP_ID = "http_id"
CONF_SSL = "ssl"
CONF_VERIFY_SSL = "verify_ssl"

# update.cgi exec targets
EXEC_DEVLIST = "devlist"
EXEC_NETDEV = "netdev"
EXEC_SYSINFO = "sysinfo"

# Sensor unique-id suffixes
SENSOR_WAN_RX = "wan_rx"
SENSOR_WAN_TX = "wan_tx"
SENSOR_LAN_RX = "lan_rx"
SENSOR_LAN_TX = "lan_tx"
SENSOR_WLAN0_RX = "wlan0_rx"
SENSOR_WLAN0_TX = "wlan0_tx"
SENSOR_UPTIME = "uptime"
SENSOR_LOAD_1 = "load_1m"
SENSOR_LOAD_5 = "load_5m"
SENSOR_LOAD_15 = "load_15m"
SENSOR_MEM_TOTAL = "mem_total"
SENSOR_MEM_FREE = "mem_free"
SENSOR_MEM_USED = "mem_used"
SENSOR_CONNECTED_DEVICES = "connected_devices"
