from enum import Enum

from colors import colors


class LogLevel(Enum):
    INFO = 1
    WARNING = 2
    ERROR = 3
    SUCCESS = 4

class Status(str, Enum):
    INITIALIZING: str = "initializing",
    DOWNLOADING: str = "downloading",
    COMPLETED: str = "completed",
    ERROR: str = "error"

def color(text: str, level: LogLevel) -> str:
    if level == LogLevel.WARNING:
        return colors.yellow(text)
    if level == LogLevel.ERROR:
        return colors.red(text)
    if level == LogLevel.SUCCESS:
        return colors.green(text)
    return text


class DownloaderStopped(Exception):
    pass


class DownloaderError(Exception):
    pass
