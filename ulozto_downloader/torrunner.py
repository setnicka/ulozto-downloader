import socket
import stem.process
import os
import uuid
import shutil


class TorRunner:
    """Running stem tor instance"""

    def _port_not_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) != 0

    def _two_free_ports(self, at):  # TODO => to torrunner class
        max_port = 65535
        ports = []
        while at < max_port:
            if len(ports) == 2:
                break

            if self._port_not_use(at):
                ports.append(at)
            at += 1
        return (ports[0], ports[1])

    @staticmethod
    def get_tor_ready(line):
        print(line)  # log
        if "Bootstrapped 100%" in line:
            print("TOR is ready, download links started")

    def start(self):
        print("make datadir")
        self.ddir = "tor_data_" + str(uuid.uuid4())
        os.mkdir(self.ddir)
        print("Write torrc")
        self.tor_ports = self._two_free_ports(41000)
        config = "SocksPort " + str(self.tor_ports[0]) + "\n"
        config += "ControlPort " + str(self.tor_ports[1]) + "\n"
        config += "DataDirectory " + self.ddir + "\n"
        config += "CookieAuthentication 1\n"
        c = open(os.path.join(self.ddir, "torrc"), "w")
        c.write(config)
        c.close()

        self.process = stem.process.launch_tor(
            torrc_path=os.path.join(self.ddir, "torrc"),
            init_msg_handler=TorRunner.get_tor_ready)
        print(self.process)

    def stop(self):
        print("Terminating tor..")
        if hasattr(self, "process"):
            self.process.terminate()

        print("Remove tor data dir: " + self.ddir)

        if os.path.exists(self.ddir):
            shutil.rmtree(self.ddir, ignore_errors=True)