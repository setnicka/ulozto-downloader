from __future__ import annotations

from typing import Callable

import stem.process
import stem.control
import os
import uuid

from uldlib import const
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
        self._create_temp_directory()

    def _create_temp_directory(self) -> None:
        """
        Creates Tor data directory if not exists.
        """
        dir_path = os.path.join(self.temp_dir, f"{const.TOR_DATA_DIR_PREFIX}{uuid.uuid4()}")
        os.makedirs(dir_path, exist_ok=True)

    def start(self) -> TorRunner:
        """
        Starts the Tor process with the given configuration.
        """
        try:
            self.tor_process = stem.process.launch_tor_with_config(config=TOR_CONFIG)
            self.log_func("TOR started")
        except Exception as e:
            self.log_func(f"Unable to start TOR: {e}")
            raise
        return self

    def launch(self) -> TorRunner:
        """
        Launches the Tor process if it has not been started.
        """
        if not self.tor_process:
            self.start()
        return self

    def reload(self) -> TorRunner:
        """
        Reloads the Tor process with a new circuit.
        """
        CONTROL_PORT = int(TOR_CONFIG.get("ControlPort"))
        with stem.control.Controller.from_port(port=CONTROL_PORT) as controller:
            controller.authenticate()
            controller.signal(stem.Signal.NEWNYM)
        return self

    def stop(self) -> TorRunner:
        """
        Stops the Tor process.
        """
        if not self.tor_process:
            return self
        self.tor_process.kill()
        return self
