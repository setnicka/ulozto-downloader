import socket
import stem.process
from stem.control import Controller
from appdirs import user_cache_dir
from typing import List
import os
import shutil
import re
import threading
import time

class MultiTor:
    """Run multiple instances of TorRunner in own threaded Tor army.."""

    size: int
    cache: str
    tors: List[threading.Thread]

    def __init__(self, size: int):
        self.size = size
        
        self.tors = []

        #TODO create dirs for each tor and star each TOR instance in own thread

    

class TorRunner:
    """Running stem tor instance indexed by number in cache data dir"""
    def __init__(self, idx:int):
        self.idx = idx
        self.ddir = os.path.join(user_cache_dir(appname="py-multitor"), "tor-" + str(self.idx))

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

    def start(self, log_func):
        os.makedirs(self.ddir, exist_ok=True)
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
        
        #time.sleep(0.5) ! now is cached to py-multitor in cache directory
        #if os.path.exists(self.ddir):
        #    shutil.rmtree(self.ddir, ignore_errors=False)
        #    print(f"Removed tor data dir: {self.ddir}")

    def __del__(self):
        self.stop()
