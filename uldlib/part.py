import threading
import time

from datetime import timedelta
from typing import Tuple

from uldlib.utils import LogLevel
from uldlib.segfile import SegFileWriter


class DownloadPart:
    id: int
    writer: SegFileWriter
    download_url: str

    success: bool = False
    exception: Exception = None

    # Lock and protected variables (used by status thread)
    lock: threading.Lock
    started: bool
    completed: bool
    error: bool
    warning: bool
    status: str
    start_time: float
    completion_time: float
    size: int
    d_now: int
    d_total: int

    def __init__(self, writer: SegFileWriter):
        self.writer = writer
        self.id = writer.id
        self.lock = threading.Lock()

        # Init empty status
        self.started = False
        self.completed = False
        self.error = False
        self.status = ""
        self.size = writer.size
        self.d_now = 0
        self.d_total = writer.written

    def set_status(self, status: str, error: bool = False, warning: bool = False):
        self.lock.acquire()
        self.status = status
        self.error = error
        self.warning = warning
        self.lock.release()

    def get_frontend_status(self) -> Tuple[str, LogLevel, int]:
        """
        Returns status line for given part
        """

        level = LogLevel.INFO
        self.lock.acquire()
        downloaded = self.d_total

        if self.error:
            msg = self.status if self.status else "ERROR: Unknown error"
            level = LogLevel.ERROR
        elif self.warning:
            msg = self.status if self.status else "WARNING: Unknown warning"
            level = LogLevel.WARNING
        elif self.status and self.completed:
            msg = self.status
            level = LogLevel.SUCCESS
        elif self.status:
            msg = self.status
        elif self.completed:
            elapsed = self.completion_time - self.start_time
            speed = self.d_now / elapsed if elapsed > 0 else 0
            msg = "Successfully downloaded {}{} MB in {} (speed {} KB/s)".format(
                round(self.d_now / 1024**2, 2),
                "" if self.d_now == self.d_total else (
                    "/"+str(round(self.d_total / 1024**2, 2))
                ),
                str(timedelta(seconds=round(elapsed))),
                round(speed / 1024, 2)
            )
            level = LogLevel.SUCCESS
        else:
            elapsed = time.time() - self.start_time
            speed = self.d_now / elapsed if elapsed > 0 else 0
            # remaining time in seconds:
            remaining = (self.size - self.d_total) / speed if speed > 0 else 0

            msg = "{:.2f}%\t{:.2f}/{:.2f} MB\tspeed: {:.2f} KB/s\telapsed: {}\tremaining: {}".format(
                round(self.d_total / self.size * 100, 2),
                round(self.d_total / 1024**2, 2), round(self.size / 1024**2, 2),
                round(speed / 1024, 2),
                str(timedelta(seconds=round(elapsed))),
                str(timedelta(seconds=round(remaining))),
            )

        self.lock.release()
        return (msg, level, downloaded)
