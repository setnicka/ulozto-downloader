from enum import Enum

from colors import colors


class LogLevel(Enum):
    INFO = 1
    WARNING = 2
    ERROR = 3
    SUCCESS = 4


def color(text: str, level: LogLevel) -> str:
    return {
        LogLevel.SUCCESS: colors.green(text),
        LogLevel.WARNING: colors.yellow(text),
        LogLevel.ERROR: colors.red(text)
    }.get(level, text)

