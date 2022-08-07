from uldlib.segfile import SegFileWriter


class DownloadPart:
    id: int
    writer: SegFileWriter
    download_url: str

    success: bool = False
    exception: Exception = None

    start_time: float

    def __init__(self, writer: SegFileWriter):
        self.writer = writer
        self.id = writer.id
