import os
from typing import Callable
from urllib.request import urlretrieve

import stem.process
import stem.control
from uldlib import const
from uldlib.utils import get_available_port

sockPort = get_available_port(9050)
controlPort = get_available_port(9051, skip=[sockPort])

TOR_CONFIG = {
    'SocksPort': f"{sockPort}",
    "ControlPort": f"{controlPort}",
    'SocksListenAddress': '127.0.0.1',
    'SocksPolicy': 'accept 127.0.0.1',
    'CookieAuthentication': '1',
    'ExcludeExitNodes': const.TOR_COUNTRY_BLACKLIST, # Some countries are blocked on Ulozto, so better to avoid Tor exiting through those to speed things up.
    'StrictNodes': '1',
    'GeoIPFile': f'{const.GEOIP_FILENAME}',
    'GeoIPv6File': f'{const.GEOIP6_FILENAME}',
    'Log': [
        'NOTICE stdout',
        'ERR file ./error.log'
    ],
}


class TorRunner:
    """
    A class that manages running and stopping a Tor process.
    """

    def __init__(self, temp_dir: str, log_func: Callable) -> None:
        """
        Initializes a TorRunner instance with a given data directory and log function.

        Args:
            temp_dir (str): the directory where the temporary data will be stored.
            log_func (Callable): a function that will be called to log messages.
        """
        self.tor_process = None
        self.log_func = log_func
        self.temp_dir = temp_dir
        self.proxies = {
            'http': f'socks5://127.0.0.1:{TOR_CONFIG.get("SocksPort")}',
            'https': f'socks5://127.0.0.1:{TOR_CONFIG.get("SocksPort")}'
        }

        def reporthook(blocknum, block_size, total_size):
            """
            Credits to jfs from https://stackoverflow.com/questions/13881092/download-progressbar-for-python-3
            """
            readsofar = blocknum * block_size
            if total_size > 0:
                percent = readsofar * 1e2 / total_size
                self.log_func("Downloading GeoIP DB: %5.1f%% %*d / %d" % (
                    percent, len(str(total_size)), readsofar, total_size))
            else:  # total size is unknown
                self.log_func("Downloading GeoIP DB: read %d" % (readsofar))

        # TODO: Add a feature to autodetect and update GeoIP DBs when never versions are available
        
        if not os.path.exists(const.GEOIP_FILENAME):
            self.log_func(f"Downloading Tor GeoIP DB from {const.TOR_GEOIP_DB_DOWNLOAD_URL}")
            # download into temp file in order to detect incomplete downloads
            db_temp_path = f"{const.GEOIP_FILENAME}.tmp"
            urlretrieve(const.TOR_GEOIP_DB_DOWNLOAD_URL, db_temp_path, reporthook)
            self.log_func("Downloading of the GeoIP DB finished")

            # rename temp DB
            os.rename(db_temp_path, const.GEOIP_FILENAME)

        if not os.path.exists(const.GEOIP6_FILENAME):
            self.log_func(f"Downloading Tor GeoIPv6 DB from {const.TOR_GEOIP6_DB_DOWNLOAD_URL}")
            # download into temp file in order to detect incomplete downloads
            db_temp_path = f"{const.GEOIP6_FILENAME}.tmp"
            urlretrieve(const.TOR_GEOIP6_DB_DOWNLOAD_URL, db_temp_path, reporthook)
            self.log_func("Downloading of the GeoIPv6 DB finished")

            # rename temp DB
            os.rename(db_temp_path, const.GEOIP6_FILENAME)

    def start(self) -> None:
        """
        Starts the Tor process with the given configuration.
        """
        try:
            self.tor_process = stem.process.launch_tor_with_config(config=TOR_CONFIG)
            self.log_func("TOR started")
        except Exception as e:
            self.log_func(f"Unable to start TOR: {e}")
            raise

    def launch(self) -> None:
        """
        Launches the Tor process if it has not been started.
        """
        if not self.tor_process:
            self.start()

    @staticmethod
    def reload() -> None:
        """
        Reloads the Tor process with a new circuit.
        """
        CONTROL_PORT = int(TOR_CONFIG.get("ControlPort"))
        with stem.control.Controller.from_port(port=CONTROL_PORT) as controller:
            controller.authenticate()
            controller.signal(stem.Signal.NEWNYM)

    def stop(self) -> None:
        """
        Stops the Tor process if running.
        """
        if self.tor_process:
            self.tor_process.kill()
