from abc import abstractmethod
from datetime import timedelta
from traceback import print_exc
import colors
import os
import sys
import time
import threading
from typing import Dict, List, Tuple

from uldlib.const import CLI_STATUS_STARTLINE
from uldlib.part import DownloadPart
from uldlib.utils import LogLevel


class DownloadInfo:
    filename: str
    url: str
    download_type: str
    total_size: int
    part_size: int
    parts: int


class Frontend():

    @abstractmethod
    def captcha_log(self, msg: str, level: LogLevel = LogLevel.INFO):
        pass

    @abstractmethod
    def captcha_stats(self, stats: Dict[str, int]):
        pass

    @abstractmethod
    def main_log(self, msg: str, level: LogLevel = LogLevel.INFO):
        pass

    @abstractmethod
    def prompt(self, msg: str, level: LogLevel = LogLevel.INFO) -> str:
        pass

    @abstractmethod
    def run(self, parts: List[DownloadPart], stop_event: threading.Event, terminate_func):
        pass


class ConsoleFrontend(Frontend):
    cli_initialized: bool

    last_log: Tuple[str, LogLevel]

    last_captcha_log: Tuple[str, LogLevel]
    last_captcha_stats: Dict[str, int]

    def __init__(self):
        self.cli_initialized = False
        self.last_log = ("", LogLevel.INFO)
        self.last_captcha_log = ("", LogLevel.INFO)
        self.last_captcha_stats = None

    def captcha_log(self, msg: str, level: LogLevel = LogLevel.INFO):
        self.last_captcha_log = (msg, level)
        if not self.cli_initialized:
            sys.stdout.write("[Link solve]\t" + msg + "\r")

    def captcha_stats(self, stats: Dict[str, int]):
        self.last_captcha_stats = stats

    def main_log(self, msg: str, level: LogLevel = LogLevel.INFO):
        self.last_log = (msg, level)

        if self.cli_initialized:
            return
        print(self._color(msg, level))

    def prompt(self, msg: str, level: LogLevel = LogLevel.INFO) -> str:
        print(self._color(msg, level), end="")
        return input().strip()

    @staticmethod
    def _stat_fmt(stats: Dict[str, int]):
        count = colors.blue(stats['all'])
        ok = colors.green(stats['ok'])
        bad = colors.red(stats['bad'])
        lim = colors.red(stats['lim'])
        blo = colors.red(stats['block'])
        net = colors.red(stats['net'])
        return f"[Ok: {ok} / {count}] :( [Badcp: {bad} Limited: {lim} Censored: {blo} NetErr: {net}]"

    @staticmethod
    def _print(text, x=0, y=0):
        sys.stdout.write("\033[{};{}H".format(y, x))
        sys.stdout.write("\033[K")
        sys.stdout.write(text)
        sys.stdout.flush()

    @staticmethod
    def _color(text: str, level: LogLevel) -> str:
        if level == LogLevel.WARNING:
            return colors.yellow(text)
        if level == LogLevel.ERROR:
            return colors.red(text)
        if level == LogLevel.SUCCESS:
            return colors.green(text)
        return text

    def run(self, info: DownloadInfo, parts: List[DownloadPart], stop_event: threading.Event, terminate_func):
        try:
            self._loop(info, parts, stop_event)
        except Exception:
            if self.cli_initialized:
                y = info.parts + CLI_STATUS_STARTLINE + 4
                sys.stdout.write("\033[{};{}H".format(y, 0))
                sys.stdout.write("\033[?25h")  # show cursor
                self.cli_initialized = False
                print("")
            print_exc()
            terminate_func()

    def _loop(self, info: DownloadInfo, parts: List[DownloadPart], stop_event: threading.Event):
        os.system('cls' if os.name == 'nt' else 'clear')
        sys.stdout.write("\033[?25l")  # hide cursor
        self.cli_initialized = True

        print(colors.blue("File:\t\t") + colors.bold(info.filename))
        print(colors.blue("URL:\t\t") + info.url)
        print(colors.blue("Download type:\t") + info.download_type)
        print(colors.blue("Size / parts: \t") +
              colors.bold(f"{round(info.total_size / 1024**2, 2)}MB => " +
              f"{info.parts} x {round(info.part_size / 1024**2, 2)}MB"))

        t_start = time.time()
        s_start = 0
        for part in parts:
            (_, _, size) = part.get_frontend_status()
            s_start += size
        last_bps = [(s_start, t_start)]

        y = 0

        while True:
            if stop_event.is_set():
                break

            t = time.time()
            # Get parts info
            lines = []
            s = 0
            for part in parts:
                (line, level, size) = part.get_frontend_status()
                lines.append(self._color(line, level))
                s += size

            # Print parts
            for (line, part) in zip(lines, parts):
                self._print(
                    colors.blue(f"[Part {part.id}]") + f"\t{line}",
                    y=(part.id + CLI_STATUS_STARTLINE))

            y = info.parts + CLI_STATUS_STARTLINE

            # Print CAPTCHA/TOR status
            (msg, level) = self.last_captcha_log
            self._print(
                colors.yellow("[Link solve]\t") +
                self._color(msg, level),
                y=y
            )
            y += 1
            if self.last_captcha_stats is not None:
                self._print(
                    colors.yellow("\t\t") + self._stat_fmt(self.last_captcha_stats),
                    y=y
                )
                y += 1

            # Print overall progress line
            if t == t_start:
                total_bps = 0
                now_bps = 0
            else:
                total_bps = (s - s_start) / (t - t_start)
                # Average now bps for last 10 measurements
                if len(last_bps) >= 10:
                    last_bps = last_bps[1:]
                (s_last, t_last) = last_bps[0]
                now_bps = (s - s_last) / (t - t_last)
                last_bps.append((s, t))

            remaining = (info.total_size - s) / total_bps if total_bps > 0 else 0

            self._print(colors.yellow(
                f"[Progress]\t"
                f"{(s / 1024 ** 2):.2f} MB"
                f" ({(s / info.total_size * 100):.2f} %)"
                f"\tavg. speed: {(total_bps / 1024 ** 2):.2f} MB/s"
                f"\tcurr. speed: {(now_bps / 1024 ** 2):.2f} MB/s"
                f"\tremaining: {timedelta(seconds=round(remaining))}"),
                y=y
            )
            y += 1

            # Print last log message
            (msg, level) = self.last_log
            self._print(
                colors.yellow("[STATUS]\t") +
                self._color(msg, level),
                y=y
            )
            y += 1

            time.sleep(0.5)

        if self.cli_initialized:
            sys.stdout.write("\033[{};{}H".format(y + 2, 0))
            sys.stdout.write("\033[?25h")  # show cursor
            self.cli_initialized = False

        elapsed = time.time() - t_start
        # speed in bytes per second:
        speed = (s - s_start) / elapsed if elapsed > 0 else 0
        print(colors.blue("Statistics:\t") + "Downloaded {}{} MB in {} (average speed {} MB/s)".format(
            round((s - s_start) / 1024**2, 2),
            "" if s_start == 0 else (
                "/"+str(round(info.total_size / 1024**2, 2))
            ),
            str(timedelta(seconds=round(elapsed))),
            round(speed / 1024**2, 2)
        ))
