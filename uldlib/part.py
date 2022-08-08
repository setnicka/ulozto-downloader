import threading

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
