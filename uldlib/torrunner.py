import socket
import sys

import stem.process
from stem.control import Controller

import os
import uuid
import shutil
import re

from uldlib import const
from uldlib.utils import LogLevel


class TorRunner:
    """Running stem tor instance"""
    ddir: str

    def __init__(self, ddir: str = ""):
        self.proxies = None
        self.torRunning = False
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

    def launch(self, log_func):
        if not self.torRunning:
            print("Starting TOR...")
            # tor started after cli initialized
            try:
                self.start(log_func=log_func)
                self.torRunning = True
                self.proxies = {
                    'http': 'socks5://127.0.0.1:' + str(self.tor_ports[0]),
                    'https': 'socks5://127.0.0.1:' + str(self.tor_ports[0])
                }

            except OSError as e:
                _error_net_stat(
                    f"Tor start failed: {e}, exiting.. try run program again..", log_func)
                # remove tor data
                if os.path.exists(self.ddir):
                    shutil.rmtree(self.ddir, ignore_errors=True)
                sys.exit(1)

    def start(self, log_func):
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
                log_func(f"Tor: {msg[0]}")  # log
            if "Bootstrapped 100%" in line:
                log_func("TOR is ready, download links started")

        self.process = stem.process.launch_tor(
            torrc_path=os.path.join(self.ddir, "torrc"),
            init_msg_handler=get_tor_ready, close_output=True)

    def reload(self):
        self.ctrl = Controller.from_port(port=self.tor_ports[1])
        self.ctrl.authenticate()
        self.ctrl.signal("RELOAD")

    def stop(self):
        if hasattr(self, "process"):
            print("Terminating tor..")
            self.process.terminate()
            if self.process.wait(10) is None:
                print("Killing zombie tor process.")
                self.process.kill()

        try:
            self.process.wait(5)
        except:
            pass

        if os.path.exists(self.ddir):
            shutil.rmtree(self.ddir, ignore_errors=True)
            print(f"Removed tor data dir: {self.ddir}")

    def __del__(self):
        self.stop()


def _error_net_stat(self, err, log_func):
    self.stats["all"] += 1
    log_func(f"Network error get new TOR connection: {err}", level=LogLevel.ERROR)
    self.stats["net"] += 1