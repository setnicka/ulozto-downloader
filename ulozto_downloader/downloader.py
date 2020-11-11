import os
import sys
import multiprocessing as mp
import time
from datetime import timedelta
from types import FunctionType
import requests

from .page import Page

CLI_STATUS_STARTLINE = 6


def print_status(id, text):
    """Print status line for specified worker to the console.

        Arguments:
            id (int): ID of the worker
            text (str): Message to write
    """

    sys.stdout.write("\033[{};{}H".format(id + CLI_STATUS_STARTLINE, 0))
    sys.stdout.write("\033[K")
    sys.stdout.write("[Part {}]\t{}".format(id, text))
    sys.stdout.flush()


def download_part(part):
    """Download given part of the download.

        Arguments:
            part (dict): Specification of the part to download
    """

    id = part['id']
    print_status(id, "Starting download")

    part['started'] = time.time()
    part['now_downloaded'] = 0

    # Note the stream=True parameter
    r = requests.get(part['download_url'], stream=True, allow_redirects=True, headers={
        "Range": "bytes={}-{}".format(part['from'] + part['downloaded'], part['to'])
    })
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

                print_status(id, "{}%\t{:.2f}/{:.2f}MB\tspeed: {:.2f} KB/s\telapsed: {}\tremaining: {}".format(
                    round(part['downloaded'] / part['size'] * 100, 1),
                    round(part['downloaded'] / 1024**2, 2), round(part['size'] / 1024**2, 2),
                    round(speed / 1024, 2),
                    str(timedelta(seconds=round(elapsed))),
                    str(timedelta(seconds=round(remaining))),
                ))

    part['elapsed'] = time.time() - part['started']
    print_status(id, "Successfully downloaded {}MB in {}".format(
        round(part['downloaded'] / 1024**2, 2),
        str(timedelta(seconds=round(part['elapsed']))),
    ))


class Downloader:
    cli_initialized: bool
    terminating: bool
    processes: slice
    captcha_solve_func: FunctionType
    parts: int

    def __init__(self, captcha_solve_func):
        self.captcha_solve_func = captcha_solve_func
        self.cli_initialized = False

    def terminate(self):
        self.terminating = True
        if self.cli_initialized:
            sys.stdout.write("\033[{};{}H".format(self.parts + CLI_STATUS_STARTLINE + 2, 0))
            self.cli_initialized = False
        print('Terminating download. Please wait for stopping all processes.')
        for p in self.processes:
            p.terminate()
        print('Download terminated.')
        return

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
        self.target_dir = target_dir
        self.terminating = False

        # 1. Prepare downloads
        print("Starting downloading for url '{}'".format(url))
        # 1.1 Get all needed information
        print("Getting info (filename, filesize, ...)")
        try:
            page = Page(url)
            page.parse()
        except RuntimeError as e:
            print('Cannot download file: ' + str(e))
            sys.exit(1)

        # Do check
        output_filename = os.path.join(target_dir, page.filename)
        if os.path.isfile(output_filename):
            print("WARNING: File '{}' already exists, overwrite it? [y/n] ".format(output_filename), end="")
            if input().strip() != 'y':
                sys.exit(1)

        isCAPTCHA = False
        if page.slowDownloadURL is not None:
            print("You are lucky, this is slow direct download without CAPTCHA :)")
            download_url = page.slowDownloadURL
        else:
            print("CAPTCHA protected download - CAPTCHA challenges will be displayed")
            isCAPTCHA = True
            download_url = page.get_captcha_download_link(captcha_solve_func=self.captcha_solve_func)

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
        os.system('clear')
        self.cli_initialized = True
        print("File: {}\nURL: {}\nSize: {}MB\nDownload type: {}\nParts: {} x {}MB".format(
            page.filename, url,
            round(total_size / 1024**2, 2),
            "CAPTCHA protected" if isCAPTCHA else "slow direct download",
            parts,
            round(part_size / 1024**2, 2),
        ))
        for part in downloads:
            if isCAPTCHA:
                print_status(part['id'], "Waiting for CAPTCHA...")
            else:
                print_status(part['id'], "Waiting for download to start...")

        # 3. Start all downloads
        for part in downloads:
            if self.terminating:
                return
            id = part['id']
            part['size'] = part['to'] - part['from'] + 1

            # Test if the file isn't downloaded from previous download. If so, try to continue
            if os.path.isfile(part['filename']):
                part['downloaded'] = os.path.getsize(part['filename'])
                if part['downloaded'] == part['size']:
                    print_status(id, "Already downloaded from previous run, skipping")
                    continue

            if isCAPTCHA:
                # Reuse already solved CAPTCHA challenge for the first not downloaded part
                if download_url is not None:
                    part['download_url'] = download_url
                    download_url = None
                else:
                    print_status(id, "Solving CAPTCHA...")
                    part['download_url'] = page.get_captcha_download_link(
                        captcha_solve_func=self.captcha_solve_func,
                        print_func=lambda msg: print_status(id, msg)
                    )
            else:
                part['download_url'] = download_url

            # Start download process in another process (parallel):
            p = mp.Process(target=download_part, args=(part,))
            p.start()
            self.processes.append(p)

        # 4. Wait for all downloads to finish
        success = True
        for p in self.processes:
            p.join()
            if p.exitcode != 0:
                success = False

        sys.stdout.write("\033[{};{}H".format(parts + CLI_STATUS_STARTLINE + 2, 0))
        self.cli_initialized = False
        if not success:
            print("Failure of one or more downloads, exiting")
            sys.exit(1)

        # 5. Concatenate all parts into final file and remove partial files
        print("All downloads finished, merging files...")
        with open(output_filename, "wb") as outfile:
            for part in downloads:
                with open(part['filename'], "rb") as infile:
                    outfile.write(infile.read())

        for part in downloads:
            os.remove(part['filename'])

        print("All files merged, output file is '{}'".format(output_filename))
