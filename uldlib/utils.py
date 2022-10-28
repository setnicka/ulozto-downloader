from enum import Enum

from colors import colors


class LogLevel(Enum):
    INFO = 1
    WARNING = 2
    ERROR = 3
    SUCCESS = 4


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
