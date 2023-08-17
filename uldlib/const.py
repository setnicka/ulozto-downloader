CLI_STATUS_STARTLINE = 5
XML_HEADERS = {
    "Accept-Encoding": "gzip",
    "X-Requested-With": "XMLHttpRequest",
    # "User-Agent": "Go-http-client/1.1",
}
DOWNPOSTFIX = '.udown'
CACHEPOSTFIX = '.ucache'
DOWN_CHUNK_SIZE = 20480
OUTFILE_WRITE_BUF = 20480
DEFAULT_CONN_TIMEOUT = 30
DEFAULT_CF_TIMEOUT = 90
DEFAULT_CF_ENDPOINT = "http://127.0.0.1:8191/v1"
MODEL_DOWNLOAD_URL = "https://github.com/JanPalasek/ulozto-captcha-breaker/releases/download/v2.2/model.tflite"
TOR_DATA_DIR_PREFIX = "tor_data_dir_"
MODEL_FILENAME = "model.tflite"
TOR_GEOIP_DB_DOWNLOAD_URL = "https://github.com/torproject/tor/raw/main/src/config/geoip"
TOR_GEOIP6_DB_DOWNLOAD_URL = "https://github.com/torproject/tor/raw/main/src/config/geoip6"
GEOIP_FILENAME = "geoip.db"
GEOIP6_FILENAME = "geoip6.db"
TOR_COUNTRY_BLACKLIST = "{de}"