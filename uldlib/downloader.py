from .const import CLI_STATUS_STARTLINE, DOWNPOSTFIX, DOWN_CHUNK_SIZE, DEFAULT_CONN_TIMEOUT
from . import utils
from .torrunner import TorRunner
from .segfile import SegFileLoader, SegFileMonitor
from .page import Page
from .part import DownloadPart
import colors
import requests
import os
from queue import Queue
import sys
import threading
import time
from datetime import timedelta
from types import FunctionType
from typing import List



class Downloader:
    cli_initialized: bool
    terminating: bool
    threads: List[threading.Thread]
    captcha_thread: threading.Thread = None
    monitor: threading.Thread = None
    captcha_solve_func: FunctionType
    download_url_queue: Queue
    parts: int
    stop_download: threading.Event
    stop_captcha: threading.Event
    stop_monitor: threading.Event

    def __init__(self, captcha_solve_func):
        self.captcha_solve_func = captcha_solve_func
        self.cli_initialized = False
        self.monitor = None
        self.conn_timeout = None

        self.stop_download = threading.Event()
        self.stop_captcha = threading.Event()
        self.stop_monitor = threading.Event()

    def terminate(self):
        self.terminating = True
        if self.cli_initialized:
            sys.stdout.write("\033[{};{}H".format(
                self.parts + CLI_STATUS_STARTLINE + 2, 0))
            sys.stdout.write("\033[?25h")  # show cursor
            self.cli_initialized = False

        print('Terminating download. Please wait for stopping all threads.')
        self.stop_captcha.set()
        self.stop_download.set()
        for p in self.threads:
            p.join()
        print('Download terminated.')
        self.stop_monitor.set()
        if self.captcha_thread:
            self.captcha_thread.join()
        if self.monitor:
            self.monitor.join()
        print('End download monitor')

    def _captcha_print_func_wrapper(self, text):
        if not self.cli_initialized:
            sys.stdout.write(colors.blue(
                "[Link solve]\t") + text + "\033[K\r")
        else:
            utils.print_captcha_status(text, self.parts)

    def _captcha_breaker(self, page, parts):
        msg = ""
        if page.isDirectDownload:
            msg = "Solve direct dlink .."
        else:
            msg = "Solve CAPTCHA dlink .."

        # utils.print_captcha_status(msg, parts)
        for url in self.captcha_download_links_generator:
            if self.stop_captcha.is_set():
                break
            utils.print_captcha_status(msg, parts)
            self.download_url_queue.put(url)

    def _save_progress(self, filename, parts, size, interval_sec):

        m = SegFileMonitor(filename)

        t_start = time.time()
        s_start = m.size()
        last_bps = [(s_start, t_start)]

        while True:
            time.sleep(interval_sec)

            if self.stop_monitor.is_set():
                m.clean()
                break

            s = m.size()
            t = time.time()

            total_bps = (s - s_start) / (t - t_start)

            # Average now bps for last 10 measurements
            if len(last_bps) >= 10:
                last_bps = last_bps[1:]
            (s_last, t_last) = last_bps[0]
            now_bps = (s - s_last) / (t - t_last)
            last_bps.append((s, t))

            remaining = (size - s) / total_bps if total_bps > 0 else 0

            utils.print_saved_status(
                f"{(s / 1024 ** 2):.2f} MB"
                f" ({(s / size * 100):.2f} %)"
                f"\tavg. speed: {(total_bps / 1024 ** 2):.2f} MB/s"
                f"\tcurr. speed: {(now_bps / 1024 ** 2):.2f} MB/s"
                f"\tremaining: {timedelta(seconds=round(remaining))}",
                parts
            )

    def _download_part(self, part: DownloadPart):
        try:
            self._download_part_internal(part)
            part.success = True
        except Exception as e:
            utils.print_part_status(part.id, colors.red(
                f"Error: {e}"
            ))
            part.exception = e
            part.success = False

    def _download_part_internal(self, part: DownloadPart):
        """Download given part of the download.

            Arguments:
                part (DownloadPart): Specification of the part to download
        """

        writer = part.writer
        id = part.id

        part.started = time.time()
        part.now_downloaded = 0

        while True:
            if self.stop_download.is_set():
                return

            utils.print_part_status(id, "Starting download")
            # Note the stream=True parameter
            r = requests.get(part.download_url, stream=True, allow_redirects=True, headers={
                "Range": "bytes={}-{}".format(writer.pfrom + writer.written, writer.pto),
                "Connection": "close",
            })

            if r.status_code != 429:
                break

            utils.print_part_status(id, colors.yellow(
                "Status code 429 Too Many Requests returned... will try again in few seconds"))
            time.sleep(5)

        if r.status_code != 206 and r.status_code != 200:
            utils.print_part_status(id, colors.red(
                f"Status code {r.status_code} returned: {writer.pfrom + writer.written}/{writer.pto}"))
            sys.exit(1)

        # reimplement as multisegment write file class
        for chunk in r.iter_content(chunk_size=DOWN_CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                writer.write(chunk)
                part.now_downloaded += len(chunk)
                elapsed = time.time() - part.started

                if self.stop_download.is_set():
                    # TODO: cancel the request when urllib3/requests will be able to do so
                    # (now r.close() would be blocking until all chunks downloaded)
                    return

                # Print status line downloaded and speed
                # speed in bytes per second:
                speed = part.now_downloaded / elapsed if elapsed > 0 else 0
                # remaining time in seconds:
                remaining = (writer.size - writer.written) / speed if speed > 0 else 0

                utils.print_part_status(id, "{:.2f}%\t{:.2f}/{:.2f} MB\tspeed: {:.2f} KB/s\telapsed: {}\tremaining: {}".format(
                    round(writer.written / writer.size * 100, 2),
                    round(writer.written / 1024**2,
                          2), round(writer.size / 1024**2, 2),
                    round(speed / 1024, 2),
                    str(timedelta(seconds=round(elapsed))),
                    str(timedelta(seconds=round(remaining))),
                ))

        # download end status
        r.close()
        elapsed = time.time() - part.started
        utils.print_part_status(id, colors.green("Successfully downloaded {}{} MB in {} (speed {} KB/s)".format(
            round(part.now_downloaded / 1024**2, 2),
            "" if part.now_downloaded == writer.written else (
                "/"+str(round(writer.written / 1024**2, 2))
            ),
            str(timedelta(seconds=round(elapsed))),
            round(part.now_downloaded / elapsed / 1024, 2) if elapsed > 0 else 0
        )))

        # close part file files
        writer.close()

        # reuse download link if need
        self.download_url_queue.put(part.download_url)

    def download(self, url, parts=10, target_dir="", conn_timeout=DEFAULT_CONN_TIMEOUT):
        """Download file from Uloz.to using multiple parallel downloads.
            Arguments:
                url (str): URL of the Uloz.to file to download
                parts (int): Number of parts that will be downloaded in parallel (default: 10)
                target_dir (str): Directory where the download should be saved (default: current directory)
        """
        self.url = url
        self.parts = parts
        self.target_dir = target_dir
        self.conn_timeout = conn_timeout

        self.threads = []
        self.terminating = False
        self.isLimited = False
        self.isCaptcha = False

        started = time.time()
        previously_downloaded = 0

        # 1. Prepare downloads
        print("Starting downloading for url '{}'".format(url))
        # 1.1 Get all needed information
        print("Getting info (filename, filesize, ...)")

        try:
            tor = TorRunner()
            page = Page(url, target_dir, parts, tor, self.conn_timeout)
            page.parse()

        except RuntimeError as e:
            print(colors.red('Cannot download file: ' + str(e)))
            sys.exit(1)

        # Do check - only if .udown status file not exists get question
        output_filename = os.path.join(target_dir, page.filename)
        if os.path.isfile(output_filename) and not os.path.isfile(output_filename+DOWNPOSTFIX):
            print(colors.yellow(
                "WARNING: File '{}' already exists, overwrite it? [y/n] ".format(output_filename)), end="")
            if input().strip() != 'y':
                sys.exit(1)

        if page.quickDownloadURL is not None:
            print("You are VERY lucky, this is QUICK direct download without CAPTCHA, downloading as 1 quick part :)")
            self.download_type = "fullspeed direct download (without CAPTCHA)"
            download_url = page.quickDownloadURL
            self.captcha_solve_func = None

        if page.slowDownloadURL is not None:
            self.isLimited = True
            if page.isDirectDownload:
                print("You are lucky, this is slow direct download without CAPTCHA :)")
                self.download_type = "slow direct download (without CAPTCHA)"
            else:
                self.isCaptcha = True
                print(
                    "CAPTCHA protected download - CAPTCHA challenges will be displayed\n")
                self.download_type = "CAPTCHA protected download"

            self.captcha_download_links_generator = page.captcha_download_links_generator(
                captcha_solve_func=self.captcha_solve_func,
                print_func=self._captcha_print_func_wrapper,
                stop_event=self.stop_captcha,
            )
            download_url = next(self.captcha_download_links_generator)

        head = requests.head(download_url, allow_redirects=True)
        total_size = int(head.headers['Content-Length'])

        try:
            file_data = SegFileLoader(output_filename, total_size, parts)
            writers = file_data.make_writers()
        except Exception as e:
            print(colors.red(
                f"Failed: Can not create '{output_filename}' error: {e} "))
            self.terminate()
            sys.exit()

        # 2. Initialize cli status table interface
        # if windows, use 'cls', otherwise use 'clear'
        os.system('cls' if os.name == 'nt' else 'clear')
        sys.stdout.write("\033[?25l")  # hide cursor
        self.cli_initialized = True
        page.cli_initialized = True  # for tor in Page
        print(colors.blue("File:\t\t") + colors.bold(page.filename))
        print(colors.blue("URL:\t\t") + page.url)
        print(colors.blue("Download type:\t") + self.download_type)
        print(colors.blue("Size / parts: \t") +
              colors.bold(f"{round(total_size / 1024**2, 2)}MB => " +
              f"{file_data.parts} x {round(file_data.part_size / 1024**2, 2)}MB"))

        downloads: List[DownloadPart] = [DownloadPart(w) for w in writers]

        # fill placeholder before download started
        for part in downloads:
            if page.isDirectDownload:
                utils.print_part_status(part.id, "Waiting for direct link...")
            else:
                utils.print_part_status(part.id, "Waiting for CAPTCHA...")

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

        # save status monitor
        self.monitor = threading.Thread(target=self._save_progress, args=(
            file_data.filename, file_data.parts, file_data.size, 1/3))
        self.monitor.start()

        # 3. Start all downloads fill self.threads
        for part in downloads:
            if self.terminating:
                return
            id = part.id

            if part.writer.written == part.writer.size:
                utils.print_part_status(id, colors.green(
                    "Already downloaded from previous run, skipping"))
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
                utils.print_captcha_status(
                    "All downloads started, no need to solve another CAPTCHAs..", self.parts)
            else:
                utils.print_captcha_status(
                    "All downloads started, no need to solve another direct links..", self.parts)

        # 4. Wait for all downloads to finish
        success = True
        for (t, part) in zip(self.threads, downloads):
            while t.is_alive():
                t.join(1)
            if not part.success:
                success = False

        # clear cli
        sys.stdout.write("\033[{};{}H".format(
            parts + CLI_STATUS_STARTLINE + 2, 0))
        sys.stdout.write("\033[K")
        sys.stdout.write("\033[?25h")  # show cursor
        self.cli_initialized = False

        # result end status
        if not success:
            print(colors.red("Failure of one or more downloads, exiting"))
            sys.exit(1)

        elapsed = time.time() - started
        # speed in bytes per second:
        speed = (total_size - previously_downloaded) / elapsed if elapsed > 0 else 0
        print(colors.green("All downloads finished"))
        print("Stats: Downloaded {}{} MB in {} (average speed {} MB/s)".format(
            round((total_size - previously_downloaded) / 1024**2, 2),
            "" if previously_downloaded == 0 else (
                "/"+str(round(total_size / 1024**2, 2))
            ),
            str(timedelta(seconds=round(elapsed))),
            round(speed / 1024**2, 2)
        ))
        # remove resume .udown file
        udown_file = output_filename + DOWNPOSTFIX
        if os.path.exists(udown_file):
            print(f"Delete file: {udown_file}")
            os.remove(udown_file)
