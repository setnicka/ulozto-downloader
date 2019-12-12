#!/usr/bin/python3
"""Uloz.to quick multiple sessions downloader.

It is needed to install these two packages (names of debian packages, for other systems they may be different):
    python3-tk
    python3-pil.imagetk
"""
import os
import sys
import argparse
import signal
import multiprocessing as mp
import re
import time
from datetime import timedelta
import requests

# Imports for GUI:
import tkinter as tk
from PIL import Image, ImageTk
from io import BytesIO

CLI_STATUS_STARTLINE = 6
XML_HEADERS = {"X-Requested-With": "XMLHttpRequest"}
DEFAULT_PARTS = 10

#####################


def parse_page(url):
    """Open the Uloz.to page of the download and return cookies, parsed filename and parsed form data.

        Arguments:
            url (str): URL of the page with file

        Returns:
            str: Parsed filename from the page
            str or None: URL of the slow direct download
            RequestsCookieJar: Obtained cookies from the page
            dict: Parsed data from the page to be send when requesting CAPTCHA

        Raises:
            RuntimeError
    """

    r = requests.get(url)

    if r.text.find("Soubor byl smazán") != -1:
        raise RuntimeError("File was deleted from Uloz.to")

    def parse(text, regex):
        p = re.compile(regex, re.IGNORECASE)
        result = p.findall(text)
        if len(result) == 0:
            return None
        return result[0]

    filename = parse(r.text, r'<title>(.*) \| Ulož.to</title>')

    # Some files may be download without CAPTCHA, there is special URL on the parsed page:
    # <a ... href="/file/E7jJsmR2ix73/michal-tucny-prodavac-mp3?do=slowDirectDownload">...</a>
    slowDirectDownload = parse(r.text, r'href="([^"]*\?do=slowDirectDownload)"')

    form_data = {
        # <input type="hidden" name="sign_a" id="frm-download-freeDownloadTab-freeDownloadForm-sign_a" value="85179a2a2b28fbe512b757cad9b9446a">
        'sign_a': parse(r.text, r'<input [^>]* name="sign_a" [^>]* value="([^>]*)">'),

        # <input type="hidden" name="adi" id="frm-download-freeDownloadTab-freeDownloadForm-adi" value="-2">
        'adi': parse(r.text, r'<input [^>]* name="adi" [^>]* value="([^>]*)">'),
    }

    # Check if slowDirectDownload or form data for CAPTCHA was parsed
    if slowDirectDownload is None and (form_data['sign_a'] is None or form_data['adi'] is None):
        raise RuntimeError("Cannot parse Uloz.to page to get download information, no slowDirectDownload and no CAPTCHA form data found")

    return filename, slowDirectDownload, r.cookies, form_data


def get_direct_download_link(url):
    """Get download link from given page URL.

        Arguments:
            url (str): URL of the page with file

        Returns:
            str: URL for downloading the file
    """

    page = requests.get('{}?do=slowDirectDownload'.format(url), allow_redirects=False)
    return page.headers['Location']


def get_captcha_download_link(url, print_func=print):
    """Get download link from given page URL, it calls CAPTCHA related functions.

        Arguments:
            url (str): URL of the page with file
            print_func (func): Function used for printing log (default is bultin 'print')

        Returns:
            str: URL for downloading the file
    """

    filename, _, cookies, form_data = parse_page(url)
    captcha_data = get_new_captcha(url, cookies, form_data)

    print_func("CAPTCHA image challenge...")
    while captcha_data['status'] != 'ok':
        captcha_answer = get_captcha_user_input("http:" + captcha_data['new_captcha_data']['image'])
        # print_func("CAPTCHA input from user: {}".format(captcha_answer))
        captcha_data = post_captcha_answer(url, cookies, captcha_data, captcha_answer)

        if captcha_data['status'] != 'ok':
            print_func("Wrong CAPTCHA input '{}', try again...".format(captcha_answer))

    # print_func('URL obtained: {}'.format(captcha_data['url']))
    return captcha_data['url']


def get_new_captcha(url, cookies, form_data):
    """Get CAPTCHA url and form parameters from given page.

        Arguments:
            url (str): URL of the page with file
            cookies (RequestsCookieJar): Cookies to be used for CAPTCHA request
            form_data (dict): Form data to be used for CAPTCHA request

        Returns:
            dict: Parsed JSON with parameters of the CAPTCHA
    """

    r = requests.post(url=url, data={
        "_do": "download-freeDownloadTab-freeDownloadForm-submit",
        "sign_a": form_data['sign_a'],
        'adi': form_data['adi'],
    }, headers=XML_HEADERS, cookies=cookies)
    return r.json()


def post_captcha_answer(url, cookies, captcha_data, captcha_answer):
    """Do POST request with CAPTCHA solution.

        Arguments:
            url (str): URl of the page with file
            cookies (RequestsCookieJar): Cookies to be used for CAPTCHA request
            captcha_data (dict): Form data to be used for CAPTCHA request
            captcha_answer (str): Answer to the CAPTCHA

        Returns:
            dict: Parsed JSON with results. On success it contains download URL, on failure it contains parameters of the new CAPTCHA
    """

    nfv = captcha_data['new_form_values']
    data = {
        '_do': 'download-freeDownloadTab-freeDownloadForm-submit',
        '_token_': nfv['_token_'],
        'adi': nfv['adi'],
        'captcha_type': captcha_data['version'],
        'captcha_value': captcha_answer,
        'cid': nfv['cid'],
        'hash': nfv['xapca_hash'],
        'salt': nfv['xapca_salt'],
        'sign': nfv['sign'],
        'sign_a': nfv['sign_a'],
        'timestamp': nfv['xapca_timestamp'],
        'ts': nfv['ts']
    }
    r = requests.post(url, data=data, headers=XML_HEADERS, cookies=cookies)
    return r.json()


def get_captcha_user_input(img_url):
    """Display captcha from given URL and ask user for input in GUI window.

        Arguments:
            img_url (str): URL of the image with CAPTCHA

        Returns:
            str: User answer to the CAPTCHA
    """

    root = tk.Tk()
    root.focus_force()
    root.title("Opiš kód z obrázku")
    root.geometry("300x140")  # use width x height + x_offset + y_offset (no spaces!)

    def disable_event():
        pass

    root.protocol("WM_DELETE_WINDOW", disable_event)

    u = requests.get(img_url)
    raw_data = u.content

    im = Image.open(BytesIO(raw_data))
    photo = ImageTk.PhotoImage(im)
    label = tk.Label(image=photo)
    label.image = photo
    label.pack()

    entry = tk.Entry(root)
    entry.pack()
    entry.bind('<Return>', lambda event: root.quit())
    entry.focus()

    tk.Button(root, text='Send', command=root.quit).pack()

    root.mainloop()  # Wait for user input
    value = entry.get()
    root.destroy()
    return value


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
    print_status(id, "Successfully downloaded {} in {}".format(
        round(part['downloaded'] / 1024**2, 2),
        str(timedelta(seconds=round(part['elapsed']))),
    ))


def download(url, parts=10, target_dir=""):
    """Download file from Uloz.to using multiple parallel downloads.

        Arguments:
            url (str): URL of the Uloz.to file to download

        Keyword Arguments:
            parts (int): Number of parts that will be downloaded in parallel (default: 10)
            target_dir (str): Directory where the download should be saved (default: current directory)
    """

    processes = []
    cli_initialized = False

    # 0. Register sigint handler
    def sigint_handler(sig, frame):
        if cli_initialized:
            sys.stdout.write("\033[{};{}H".format(parts + CLI_STATUS_STARTLINE + 2, 0))
        print('Interrupted, ending program. Please wait for stopping all processes.')
        for p in processes:
            p.terminate()
        print('Program terminated.')
        sys.exit(1)
    signal.signal(signal.SIGINT, sigint_handler)

    # 1. Prepare downloads
    print("Starting downloading for url '{}'".format(url))
    # 1.1 Get all needed information
    print("Getting info (filename, filesize, ...)")
    try:
        final_filename, slowDirectDownload, _, _ = parse_page(url)
    except RuntimeError as e:
        print('Cannot download file: ' + str(e))
        sys.exit(1)

    # It is CAPTCHA protected download if slowDirectDownload URL is not set
    isCAPTCHA = slowDirectDownload is None

    # Do check
    if os.path.isfile(final_filename):
        print("WARNING: File '{}' already exists, overwrite it? [y/n] ".format(final_filename), end="")
        if input().strip() != 'y':
            sys.exit(1)

    if isCAPTCHA:
        print("CAPTCHA protected download - CAPTCHA challenges will be displayed")
        download_url = get_captcha_download_link(url)
    else:
        print("You are lucky, this is slow direct download without CAPTCHA :)")
        download_url = get_direct_download_link(url)

    head = requests.head(download_url, allow_redirects=True)
    total_size = int(head.headers['Content-Length'])
    part_size = (total_size + (parts - 1)) // parts

    # 1.3 Prepare download info for parts
    downloads = [
        {
            'id': i + 1,
            'filename': os.path.join(
                target_dir,
                final_filename + ".part{0:0{width}}of{1}".format(i + 1, parts, width=len(str(parts)))
            ),
            'from': part_size * i,
            'to': min(part_size * (i + 1), total_size) - 1,
            'downloaded': 0,
        } for i in range(parts)
    ]

    # 2. Initialize cli status table interface
    os.system('clear')
    cli_initialized = True
    print("File: {}\nURL: {}\nSize: {}MB\nDownload type: {}\nParts: {} x {}MB".format(
        final_filename, url,
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
                part['download_url'] = get_captcha_download_link(url, print_func=lambda msg: print_status(id, msg))
        else:
            part['download_url'] = get_direct_download_link(url)

        # Start download process in another process (parallel):
        p = mp.Process(target=download_part, args=(part,))
        p.start()
        processes.append(p)

    # 4. Wait for all downloads to finish
    success = True
    for p in processes:
        p.join()
        if p.exitcode != 0:
            success = False

    sys.stdout.write("\033[{};{}H".format(parts + CLI_STATUS_STARTLINE + 2, 0))
    if not success:
        print("Failure of one or more downloads, exiting")
        sys.exit(1)

    # 5. Concatenate all parts into final file and remove partial files
    print("All downloads finished, merging files...")
    with open(final_filename, "wb") as outfile:
        for part in downloads:
            with open(part['filename'], "rb") as infile:
                outfile.write(infile.read())

    for part in downloads:
        os.remove(part['filename'])

    print("All files merged, output file is '{}'".format(final_filename))


###########################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Download file from Uloz.to using multiple parallel downloads.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('url', metavar='URL', type=str, help="URL from Uloz.to (tip: enter in 'quotes' because the URL contains ! sign)")
    parser.add_argument('--parts', metavar='N', type=int, default=10, help='Number of parts that will be downloaded in parallel')
    parser.add_argument('--output', metavar='DIRECTORY', type=str, default="./", help='Target directory')

    args = parser.parse_args()

    download(args.url, args.parts, args.output)
