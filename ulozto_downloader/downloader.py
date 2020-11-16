import os
import sys
import multiprocessing as mp
import time
from datetime import timedelta
from types import FunctionType
import requests
import colors

from .page import Page
from . import utils, const


class Downloader:
    cli_initialized: bool
    terminating: bool
    processes: slice
    captcha_process: mp.Process
    captcha_solve_func: FunctionType
    download_url_queue: mp.Queue
    parts: int

    def __init__(self, captcha_solve_func):
        self.captcha_solve_func = captcha_solve_func
        self.cli_initialized = False

    def terminate(self):
        self.terminating = True
        if self.cli_initialized:
            sys.stdout.write("\033[{};{}H".format(self.parts + const.CLI_STATUS_STARTLINE + 2, 0))
            sys.stdout.write("\033[?25h")  # show cursor
            self.cli_initialized = False
        print('Terminating download. Please wait for stopping all processes.')
        if self.captcha_process is not None:
            self.captcha_process.terminate()
        for p in self.processes:
            p.terminate()
        print('Download terminated.')
        return

    def _captcha_breaker(self, page, parts):
        while True:
            utils.print_captcha_status("Solving CAPTCHA...", parts)
            self.download_url_queue.put(
                page.get_captcha_download_link(
                    captcha_solve_func=self.captcha_solve_func,
                    print_func=lambda text: utils.print_captcha_status(text, parts)
                )
            )

    @staticmethod
    def _download_part(part, download_url_queue):
        """Download given part of the download.

            Arguments:
                part (dict): Specification of the part to download
        """

        id = part['id']
        utils.print_part_status(id, "Starting download")

        part['started'] = time.time()
        part['now_downloaded'] = 0

        # Note the stream=True parameter
        r = requests.get(part['download_url'], stream=True, allow_redirects=True, headers={
            "Range": "bytes={}-{}".format(part['from'] + part['downloaded'], part['to'])
        })

        if r.status_code != 206 and r.status_code != 200:
            utils.print_part_status(id, colors.red(f"Status code {r.status_code} returned"))
            raise RuntimeError(f"Download of part {id} returned status code {r.status_code}")

        with open(part['filename'], 'ab') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    part['downloaded'] += len(chunk)
                    part['now_downloaded'] += len(chunk)
                    elapsed = time.time() - part['started']

                    # Print status line
                    speed = part['now_downloaded'] / elapsed if elapsed > 0 else 0  # in bytes per second
                    remaining = (part['size'] - part['downloaded']) / speed if speed > 0 else 0  # in seconds

                    utils.print_part_status(id, "{}%\t{:.2f}/{:.2f} MB\tspeed: {:.2f} KB/s\telapsed: {}\tremaining: {}".format(
                        round(part['downloaded'] / part['size'] * 100, 1),
                        round(part['downloaded'] / 1024**2, 2), round(part['size'] / 1024**2, 2),
                        round(speed / 1024, 2),
                        str(timedelta(seconds=round(elapsed))),
                        str(timedelta(seconds=round(remaining))),
                    ))

        part['elapsed'] = time.time() - part['started']
        utils.print_part_status(id, colors.green("Successfully downloaded {}{} MB in {} (speed {} KB/s)".format(
            round(part['now_downloaded'] / 1024**2, 2),
            "" if part['now_downloaded'] == part['downloaded'] else ("/"+str(round(part['downloaded'] / 1024**2, 2))),
            str(timedelta(seconds=round(part['elapsed']))),
            round(part['now_downloaded'] / part['elapsed'] / 1024, 2) if part['elapsed'] > 0 else 0
        )))
        # Free this (still valid) download URL for next use
        download_url_queue.put(part['download_url'])

    def download(self, url, parts=10, target_dir=""):
        """Download file from Uloz.to using multiple parallel downloads.

            Arguments:
                url (str): URL of the Uloz.to file to download
                parts (int): Number of parts that will be downloaded in parallel (default: 10)
                target_dir (str): Directory where the download should be saved (default: current directory)
        """

        self.url = url
        self.parts = parts
        self.processes = []
        self.captcha_process = None
        self.target_dir = target_dir
        self.terminating = False

        started = time.time()
        previously_downloaded = 0

        # 1. Prepare downloads
        print("Starting downloading for url '{}'".format(url))
        # 1.1 Get all needed information
        print("Getting info (filename, filesize, ...)")
        try:
            page = Page(url)
            page.parse()
        except RuntimeError as e:
            print(colors.red('Cannot download file: ' + str(e)))
            sys.exit(1)

        # Do check
        output_filename = os.path.join(target_dir, page.filename)
        if os.path.isfile(output_filename):
            print(colors.yellow("WARNING: File '{}' already exists, overwrite it? [y/n] ".format(output_filename)), end="")
            if input().strip() != 'y':
                sys.exit(1)

        isCAPTCHA = False
        if page.quickDownloadURL is not None:
            print("You are VERY lucky, this is QUICK direct download without CAPTCHA, downloading as 1 quick part :)")
            download_type = "fullspeed direct download (without CAPTCHA)"
            download_url = page.quickDownloadURL
            parts = 1
            self.parts = 1
        elif page.slowDownloadURL is not None:
            print("You are lucky, this is slow direct download without CAPTCHA :)")
            download_type = "slow direct download (without CAPTCHA)"
            download_url = page.slowDownloadURL
        else:
            print("CAPTCHA protected download - CAPTCHA challenges will be displayed\n")
            download_type = "CAPTCHA protected download"
            isCAPTCHA = True
            download_url = page.get_captcha_download_link(
                captcha_solve_func=self.captcha_solve_func,
                print_func=lambda text: sys.stdout.write(colors.blue("[CAPTCHA solve]\t") + text + "\033[K\r")
            )

        head = requests.head(download_url, allow_redirects=True)
        total_size = int(head.headers['Content-Length'])
        part_size = (total_size + (parts - 1)) // parts

        # 1.3 Prepare download info for parts
        downloads = [
            {
                'id': i + 1,
                'filename': "{0}.part{1:0{width}}of{2}".format(output_filename, i + 1, parts, width=len(str(parts))),
                'from': part_size * i,
                'to': min(part_size * (i + 1), total_size) - 1,
                'downloaded': 0,
            } for i in range(parts)
        ]

        # 2. Initialize cli status table interface
        os.system('cls' if os.name == 'nt' else 'clear')  # if windows, use 'cls', otherwise use 'clear'
        sys.stdout.write("\033[?25l")  # hide cursor
        self.cli_initialized = True
        print(colors.blue("File:\t\t") + colors.bold(page.filename))
        print(colors.blue("URL:\t\t") + page.url)
        print(colors.blue("Download type:\t") + download_type)
        print(colors.blue("Total size:\t") + colors.bold("{}MB".format(round(total_size / 1024**2, 2))))
        print(colors.blue("Parts:\t\t") + "{} x {}MB".format(parts, round(part_size / 1024**2, 2)))

        for part in downloads:
            if isCAPTCHA:
                utils.print_part_status(part['id'], "Waiting for CAPTCHA...")
            else:
                utils.print_part_status(part['id'], "Waiting for download to start...")

        # Prepare queue for recycling download URLs
        self.download_url_queue = mp.Queue(maxsize=0)
        if isCAPTCHA:
            # Reuse already solved CAPTCHA
            self.download_url_queue.put(download_url)

            # Start CAPTCHA breaker in separate process
            self.captcha_process = mp.Process(target=self._captcha_breaker, args=(page, self.parts))
            self.captcha_process.start()

        # 3. Start all downloads
        for part in downloads:
            if self.terminating:
                return
            id = part['id']
            part['size'] = part['to'] - part['from'] + 1

            # Test if the file isn't downloaded from previous download. If so, try to continue
            if os.path.isfile(part['filename']):
                part['downloaded'] = os.path.getsize(part['filename'])
                previously_downloaded += part['downloaded']
                if part['downloaded'] == part['size']:
                    utils.print_part_status(id, colors.green("Already downloaded from previous run, skipping"))
                    continue

            if isCAPTCHA:
                part['download_url'] = self.download_url_queue.get()
            else:
                part['download_url'] = download_url

            # Start download process in another process (parallel):
            p = mp.Process(target=Downloader._download_part, args=(part, self.download_url_queue))
            p.start()
            self.processes.append(p)

        if isCAPTCHA:
            # no need for another CAPTCHAs
            self.captcha_process.terminate()
            utils.print_captcha_status("All downloads started, no need to solve another CAPTCHAs", self.parts)

        # 4. Wait for all downloads to finish
        success = True
        for p in self.processes:
            p.join()
            if p.exitcode != 0:
                success = False

        # Check all downloads
        checkError = False
        for part in downloads:
            if not os.path.isfile(part['filename']):
                utils.print_part_status(part['id'], colors.red(
                    f"ERROR: Part '{part['filename']}' missing on disk"
                ))
                checkError = True
                continue
            size = os.path.getsize(part['filename'])
            if size != part['size']:
                utils.print_part_status(part['id'], colors.red(
                    f"ERROR: Part '{part['filename']}' has wrong size {size} bytes (instead of {part['size']} bytes)"
                ))
                os.remove(part['filename'])
                checkError = True

        sys.stdout.write("\033[{};{}H".format(parts + const.CLI_STATUS_STARTLINE + 2, 0))
        sys.stdout.write("\033[K")
        sys.stdout.write("\033[?25h")  # show cursor
        self.cli_initialized = False
        if not success:
            print(colors.red("Failure of one or more downloads, exiting"))
            sys.exit(1)
        if checkError:
            print(colors.red("Wrong sized parts deleted, please restart the download"))
            sys.exit(1)

        # 5. Concatenate all parts into final file and remove partial files
        elapsed = time.time() - started
        speed = (total_size - previously_downloaded) / elapsed if elapsed > 0 else 0  # in bytes per second
        print(colors.green("All downloads finished"))
        print("Stats: Downloaded {}{} MB in {} (average speed {} MB/s), merging files...".format(
            round((total_size - previously_downloaded) / 1024**2, 2),
            "" if previously_downloaded == 0 else ("/"+str(round(total_size / 1024**2, 2))),
            str(timedelta(seconds=round(elapsed))),
            round(speed / 1024**2, 2)
        ))
        with open(output_filename, "wb") as outfile:
            for part in downloads:
                with open(part['filename'], "rb") as infile:
                    outfile.write(infile.read())

        for part in downloads:
            os.remove(part['filename'])

        print(colors.green("Parts merged into output file '{}'".format(output_filename)))
