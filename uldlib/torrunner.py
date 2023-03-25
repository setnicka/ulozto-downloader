from typing import Callable

import stem.process
import stem.control
from uldlib.utils import get_available_port

TOR_CONFIG = {
    'SocksPort': f"{get_available_port(9050)}",
    "ControlPort": f"{get_available_port(9051)}",
    'SocksListenAddress': '127.0.0.1',
    'SocksPolicy': 'accept 127.0.0.1',
    'CookieAuthentication': '1',
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
        Stops the Tor process and removes temp directory if exists.
        """
        if not self.tor_process:
            return None
        self.tor_process.kill()
