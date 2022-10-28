import socket
from typing import Callable

import stem.process
from stem.control import Controller
import os
import uuid
import shutil
import re

from uldlib import const
from uldlib.utils import DownloaderError


class TorRunner:
    """Running stem tor instance"""
    ddir: str
    log_func: Callable

    def __init__(self, ddir: str, log_func: Callable):
        self.proxies = None
        self.torRunning = False
        self.log_func = log_func
        uid = str(uuid.uuid4())
        self.ddir = os.path.join(ddir, f"{const.TOR_DATA_DIR_PREFIX}{uid}")

    def _port_not_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) != 0

    def _two_free_ports(self, at):
        max_port = 65535
        ports = []
        while at < max_port:
            if len(ports) == 2:
                break

            if self._port_not_use(at):
                ports.append(at)
            at += 1
        return (ports[0], ports[1])

    def launch(self):
        if self.torRunning:
            return

        self.log_func("Starting TOR...")
        # tor started after cli initialized
        try:
            self.start()
            self.torRunning = True
            self.proxies = {
                'http': 'socks5://127.0.0.1:' + str(self.tor_ports[0]),
                'https': 'socks5://127.0.0.1:' + str(self.tor_ports[0])
            }

        except OSError as e:
            # remove tor data
            if os.path.exists(self.ddir):
                shutil.rmtree(self.ddir, ignore_errors=True)
            raise DownloaderError(f"Tor start failed: {e}, exiting. Try run program again.")

    def start(self):
        os.mkdir(self.ddir)
        self.tor_ports = self._two_free_ports(41000)
        config = "SocksPort " + str(self.tor_ports[0]) + "\n"
        config += "ControlPort " + str(self.tor_ports[1]) + "\n"
        config += "DataDirectory " + self.ddir + "\n"
        config += "CookieAuthentication 1\n"
        tcpath = os.path.join(self.ddir, "torrc")
        c = open(tcpath, "w")
        c.write(config)
        c.close()

        def get_tor_ready(line):
            p = re.compile(r'Bootstrapped \d+%')
            msg = re.findall(p, line)

            if len(msg) > 0:
                self.log_func(msg[0], progress=True)
            if "Bootstrapped 100%" in line:
                self.log_func("TOR is ready, download links started")

        self.process = stem.process.launch_tor(
            torrc_path=os.path.join(self.ddir, "torrc"),
            init_msg_handler=get_tor_ready, close_output=True)

    def reload(self):
        self.ctrl = Controller.from_port(port=self.tor_ports[1])
        self.ctrl.authenticate()
        self.ctrl.signal("RELOAD")

    def stop(self):
        if not self.torRunning:
            return

        if hasattr(self, "process"):
            self.log_func("Terminating tor")
            self.process.terminate()
            if self.process.wait(10) is None:
                self.log_func("Killing zombie tor process.")
                self.process.kill()

        self.torRunning = False

        try:
            self.process.wait(5)
        except:
            pass

        if os.path.exists(self.ddir):
            shutil.rmtree(self.ddir, ignore_errors=True)
            self.log_func(f"Removed tor data dir: {self.ddir}")

    def __del__(self):
        self.stop()
