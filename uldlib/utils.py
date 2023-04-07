import socket
from enum import Enum

from colors import colors


class LogLevel(Enum):
    INFO = 1
    WARNING = 2
    ERROR = 3
    SUCCESS = 4


class Status(str, Enum):
    INITIALIZING: str = "initializing"
    DOWNLOADING: str = "downloading"
    COMPLETED: str = "completed"
    ERROR: str = "error"


def color(text: str, level: LogLevel) -> str:
    if level == LogLevel.WARNING:
        return colors.yellow(text)
    if level == LogLevel.ERROR:
        return colors.red(text)
    if level == LogLevel.SUCCESS:
        return colors.green(text)
    return text


def _is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


def get_available_port(given_port: int) -> int:
    max_attempts = 65535
    while given_port < max_attempts:
        if _is_port_available(given_port):
            return given_port
        given_port += 1
    else:
        raise ValueError("Cannot get available port")


class DownloaderStopped(Exception):
    pass


class DownloaderError(Exception):
    pass
