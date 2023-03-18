import os
from queue import Queue
import requests
import threading
import time
from typing import List, Type

from uldlib.captcha import CaptchaSolver
from uldlib.const import DOWNPOSTFIX, DOWN_CHUNK_SIZE, DEFAULT_CONN_TIMEOUT
from uldlib.frontend import DownloadInfo, Frontend
from uldlib.page import Page
from uldlib.part import DownloadPart
from uldlib.segfile import SegFileLoader
from uldlib.torrunner import TorRunner
from uldlib.utils import DownloaderError, DownloaderStopped, LogLevel


class Downloader:
    terminating: bool

    threads: List[threading.Thread]
    stop_download: threading.Event

    frontend: Type[Frontend]
    frontend_thread: threading.Thread = None
    stop_frontend: threading.Event

    captcha_solver: Type[CaptchaSolver]
    captcha_thread: threading.Thread = None
    stop_captcha: threading.Event

    download_url_queue: Queue
    parts: int
    tor: TorRunner
    page: Page

    password: str

    def __init__(self, tor: TorRunner, frontend: Type[Frontend], captcha_solver: Type[CaptchaSolver]):
        """Initialize the Downloader.

           The TorRunner could be launched or not, the .launch() method will be called when needed.
           Also it is caller responsibility to call .stop() method on the TorRunner.
        """

        self.success = None
        self.url = None
        self.filename = None
        self.output_filename = None
        self.stat_filename = None
        self.total_size = None
        self.frontend = frontend
        self.log = frontend.main_log
        self.captcha_solver = captcha_solver

        self.cli_initialized = False
        self.conn_timeout = None
        self.tor = tor

    def terminate(self, quiet: bool = False):
        if self.terminating:
            return
        self.terminating = True

        if not quiet:
            self.log('Terminating download. Please wait for stopping all threads.', level=LogLevel.WARNING)

        self.stop_download.set()
        self.stop_captcha.set()
        if self.captcha_thread and self.captcha_thread.is_alive():
            self.captcha_thread.join()
        for p in self.threads:
            if p.is_alive():
                p.join()

        if not quiet:
            self.log('Download terminated.', level=LogLevel.WARNING)

        self.stop_frontend.set()
        if self.frontend_thread and self.frontend_thread.is_alive():
            self.frontend_thread.join()

    def clean(self):
        # remove resume .udown file
        if os.path.exists(self.stat_filename):
            os.remove(self.stat_filename)
        if self.page.linkCache is not None:
            self.page.linkCache.delete_cache_file()

    def _captcha_breaker(self, page, parts):
        msg = ""
        if page.isDirectDownload:
            msg = "Solve direct dlink .."
        else:
            msg = "Solve CAPTCHA dlink .."

        try:
            for url in self.captcha_download_links_generator:
                if self.stop_captcha.is_set():
                    break
                self.captcha_solver.log(msg)
                self.download_url_queue.put(url)
        except DownloaderError as e:
            self.captcha_solver.log(str(e), level=LogLevel.ERROR)

    def _download_part(self, part: DownloadPart):
        try:
            self._download_part_internal(part)
        except Exception as e:
            part.exception = e
            part.set_status(f"Error: {e}", error=True)

    def _download_part_internal(self, part: DownloadPart):
        """Download given part of the download.

            Arguments:
                part (DownloadPart): Specification of the part to download
        """

        writer = part.writer

        part.lock.acquire()
        part.started = True
        part.start_time = time.time()
        part.lock.release()

        while True:
            if self.stop_download.is_set():
                return

            part.set_status("Starting download")
            # Note the stream=True parameter
            r = requests.get(part.download_url, stream=True, allow_redirects=True, headers={
                "Range": "bytes={}-{}".format(writer.pfrom + writer.written, writer.pto),
                "Connection": "close",
            })

            if r.status_code == 429:
                part.set_status("Status code 429 Too Many Requests returned… will try again in few seconds", warning=True)
                time.sleep(5)
            elif r.status_code == 425:
                part.set_status("Status code 425 Too Early returned… will try again in few seconds", warning=True)
                time.sleep(5)
            else:
                break

        if r.status_code != 206 and r.status_code != 200:
            part.set_status(f"Status code {r.status_code} returned: {writer.pfrom + writer.written}/{writer.pto}", error=True)
            return

        part.set_status("")

        # reimplement as multisegment write file class
        for chunk in r.iter_content(chunk_size=DOWN_CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                writer.write(chunk)

                part.lock.acquire()
                part.d_now += len(chunk)
                part.d_total += len(chunk)
                part.lock.release()

                if self.stop_download.is_set():
                    # TODO: cancel the request when urllib3/requests will be able to do so
                    # (now r.close() would be blocking until all chunks downloaded)
                    return

        # download end status
        r.close()
        part.lock.acquire()
        part.completed = True
        part.completion_time = time.time()
        part.lock.release()

        # close part file files
        writer.close()

        # reuse download link if need
        self.download_url_queue.put(part.download_url)

    def download(self, url: str, parts: int = 10, password: str = "", target_dir: str = "", temp_dir: str = "", do_overwrite: bool = False, conn_timeout=DEFAULT_CONN_TIMEOUT):
        """Download file from Uloz.to using multiple parallel downloads.
            Arguments:
                url: URL of the Uloz.to file to download
                parts: Number of parts that will be downloaded in parallel (default: 10)
                target_dir: Directory where the download should be saved (default: current directory)
                do_overwrite: Overwrite files without asking
                temp_dir: Directory where temporary files will be created (default: current directory)
                password: Optional password to access the Uloz.to file
        """
        self.url = url
        self.parts = parts
        self.conn_timeout = conn_timeout

        self.threads = []
        self.terminating = False
        self.isLimited = False
        self.isCaptcha = False

        self.stop_download = threading.Event()
        self.stop_captcha = threading.Event()
        self.stop_frontend = threading.Event()

        # 1. Prepare downloads
        self.log("Starting downloading for url '{}'".format(url))
        # 1.1 Get all needed information
        self.log("Getting info (filename, filesize, …)")

        try:
            self.page = Page(
                url=url,
                temp_dir=temp_dir,
                parts=parts,
                password=password,
                frontend=self.frontend,
                tor=self.tor,
                conn_timeout=self.conn_timeout,
            )
            page = self.page  # shortcut
            page.parse()

        except Exception as e:
            raise DownloaderError('Cannot download file: ' + str(e))

        # Check of the target is a file or directory and construct the output path accordingly
        if not os.path.isdir(target_dir) and target_dir[-1] != '/':
            # Path to a file has been provided
            self.output_filename = target_dir
        else:
            # Create the output directory if does not exist
            os.makedirs(target_dir, exist_ok = True)
            self.output_filename = os.path.join(target_dir, page.filename)
        self.filename = os.path.basename(self.output_filename)
        self.stat_filename = os.path.join(temp_dir, self.filename + DOWNPOSTFIX)

        self.log("Downloading into: '{}'".format(self.output_filename))

        # Do check - only if .udown status file not exists get question
        # .udown file is always present in cli_mode = False
        if os.path.isfile(self.output_filename) and not os.path.isfile(self.stat_filename):
            if self.frontend.supports_prompt and not do_overwrite:
                answer = self.frontend.prompt(
                    "WARNING: File '{}' already exists, overwrite it? [y/n] ".format(self.output_filename), level=LogLevel.WARNING)
                if answer != 'y':
                    raise DownloaderStopped()
            else:
                self.log("WARNING: File '{}' already exists, but .udown file not present. File will be overwritten.."
                         .format(self.output_filename), level=LogLevel.WARNING)

        info = DownloadInfo()
        info.filename = self.filename
        info.url = page.url

        if page.quickDownloadURL is not None:
            self.log("You are VERY lucky, this is QUICK direct download without CAPTCHA, downloading as 1 quick part :)")
            info.download_type = "fullspeed direct download (without CAPTCHA)"
            download_url = page.quickDownloadURL
            self.captcha_solve_func = None

        if page.slowDownloadURL is not None:
            self.isLimited = True
            if page.isDirectDownload:
                self.log("You are lucky, this is slow direct download without CAPTCHA :)")
                info.download_type = "slow direct download (without CAPTCHA)"
            else:
                self.isCaptcha = True
                self.log("CAPTCHA protected download - CAPTCHA challenges will be displayed")
                info.download_type = "CAPTCHA protected download"

            if self.isCaptcha and self.captcha_solver.cannot_solve:
                raise DownloaderError("Cannot solve CAPTCHAs, no solver available. Terminating")

            self.captcha_download_links_generator = page.captcha_download_links_generator(
                solver=self.captcha_solver, stop_event=self.stop_captcha,
            )
            download_url = next(self.captcha_download_links_generator)

        head = requests.head(download_url, allow_redirects=True)
        self.total_size = int(head.headers['Content-Length'])

        try:
            file_data = SegFileLoader(self.output_filename, self.stat_filename, self.total_size, parts)
            writers = file_data.make_writers()
        except Exception as e:
            raise DownloaderError(f"Failed: Can not create '{self.output_filename}' error: {e} ")

        info.total_size = self.total_size
        info.part_size = file_data.part_size
        info.parts = file_data.parts

        downloads: List[DownloadPart] = [DownloadPart(w) for w in writers]

        # 2. All info gathered, initialize frontend

        self.log("Download in progress")
        # fill placeholder before download started
        for part in downloads:
            if page.isDirectDownload:
                part.set_status("Waiting for direct link…")
            else:
                part.set_status("Waiting for CAPTCHA…")

        self.frontend_thread = threading.Thread(
            target=self.frontend.run,
            args=(info, downloads, self.stop_frontend, self.terminate)
        )
        self.frontend_thread.start()

        # Prepare queue for recycling download URLs
        self.download_url_queue = Queue(maxsize=0)

        # limited must use TOR and solve links or captcha
        if self.isLimited:
            # Reuse already solved links
            self.download_url_queue.put(download_url)

            # Start CAPTCHA breaker in separate process
            self.captcha_thread = threading.Thread(
                target=self._captcha_breaker, args=(page, self.parts)
            )

        cpb_started = False
        page.alreadyDownloaded = 0

        # 3. Start all downloads fill self.threads
        for part in downloads:
            if self.terminating:
                return

            if part.writer.written == part.writer.size:
                part.completed = True
                part.set_status("Already downloaded from previous run, skipping")
                page.alreadyDownloaded += 1
                continue

            if self.isLimited:
                if not cpb_started:
                    self.captcha_thread.start()
                    cpb_started = True
                part.download_url = self.download_url_queue.get()
            else:
                part.download_url = download_url

            # Start download process in another process (parallel):
            t = threading.Thread(target=self._download_part, args=(part,))
            t.start()
            self.threads.append(t)

        if self.isLimited:
            # no need for another CAPTCHAs
            self.stop_captcha.set()
            if self.isCaptcha:
                self.captcha_solver.log("All downloads started, no need to solve another CAPTCHAs…")
            else:
                self.captcha_solver.log("All downloads started, no need to solve another direct links…")

        # 4. Wait for all downloads to finish
        success = True
        for (t, part) in zip(self.threads, downloads):
            while t.is_alive():
                t.join(1)
            if part.error:
                success = False

        self.terminate(quiet=True)

        self.success = success
        # result end status
        if not success:
            raise DownloaderError("Failure of one or more downloads, exiting")

        self.log("All downloads successfully finished", level=LogLevel.SUCCESS)
