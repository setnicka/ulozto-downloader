import re
import threading
from typing import Optional, Type
from urllib.parse import urlparse, urljoin
from os import path
import requests

from uldlib.captcha import CaptchaSolver
from uldlib.frontend import LogLevel, Frontend
from uldlib.torrunner import TorRunner

from .const import XML_HEADERS, DEFAULT_CONN_TIMEOUT
from .crawler import UloztoCrawler
from .linkcache import LinkCache

from .scraper import FileMetadataScraper


def parse_single(text, regex):
    p = re.compile(regex, re.IGNORECASE)
    result = p.findall(text)
    if len(result) == 0:
        return None
    return result[0]


def strip_tracking_info(url: str):
    return url.split("#!")[0] if "#!" in url else url


class Page:
    url: str
    body: str
    baseURL: str
    slug: str
    filename: str
    slowDownloadURL: str
    quickDownloadURL: str
    captchaURL: str
    isDirectDownload: bool
    numTorLinks: int
    alreadyDownloaded: int
    password: str

    needPassword: bool = False

    linkCache: Optional[LinkCache] = None

    def __init__(self, url: str, temp_dir: str, parts: int, password: str, frontend: Frontend, tor: TorRunner, conn_timeout=DEFAULT_CONN_TIMEOUT):
        """Check given url and if it looks ok GET the Uloz.to page and save it.

            Arguments:
                url (str): URL of the page with file
                temp_dir (str): directory where .ucache file will be created
                parts (int): number of segments (parts)
                password (str): password to access the Uloz.to file
                frontend (Frontend): frontend object for password prompt (if supported)
                tor (TorRunner): tor runner instance
            Raises:
                RuntimeError: On invalid URL, deleted file or other error related to getting the page.
        """

        self.url = url
        self.temp_dir = temp_dir
        self.parts = parts
        self.tor = tor
        self.conn_timeout = conn_timeout

        self.tor.launch()  # ensure that TOR is running

        self.cli_initialized = False
        self.alreadyDownloaded = 0
        self.stats = {"all": 0, "ok": 0, "bad": 0,
                      "lim": 0, "block": 0, "net": 0}  # statistics

        self.baseURL = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(self.url))

    def parse(self):
        """Try to parse all information from the page (filename, download links, ...)

        Raises:
            RuntimeError: When mandatory fields cannot be parsed.
        """
        html_doc = UloztoCrawler(self.url).get_html_document()
        file_metadata = FileMetadataScraper(html_doc)

        self.filename = file_metadata.filename
        self.quickDownloadURL = file_metadata.quick_download_url
        if self.quickDownloadURL:
            self.quickDownloadURL = self.baseURL + self.quickDownloadURL
        self.isDirectDownload = file_metadata.is_direct_download

        self.captchaURL = file_metadata.captcha_url
        if self.captchaURL:
            self.captchaURL = self.baseURL + self.captchaURL
        self.slowDownloadURL = self.captchaURL

    def _error_net_stat(self, err, log_func):
        """print TOR network error and += stats"""
        self.stats["all"] += 1
        log_func(f"Network error get new TOR connection: {err}", level=LogLevel.ERROR)
        self.stats["net"] += 1

    def _link_validation_stat(self, resp, log_func):
        linkdata = resp.text
        self.stats["all"] += 1
        ok = False
        reload = True

        # search errors..
        good_str = "afterDownloadUrl"
        blk_str = 'blocked'
        lim_str = 'limit-exceeded'
        bcp_str = "formErrorContent"

        # msgs
        lim_msg = "IP limited TOR exit.. get new TOR session"
        blk_msg = "Blocked TOR exit IP.. get new TOR session"
        bcp_msg = "Bad captcha.. Try again using same IP"

        if good_str in linkdata:
            self.stats["ok"] += 1
            ok = True
        elif lim_str in linkdata:
            self.stats["lim"] += 1
            if not self.isDirectDownload:
                log_func(lim_msg, level=LogLevel.ERROR)
        elif blk_str in linkdata:
            self.stats["block"] += 1
            if not self.isDirectDownload:
                log_func(blk_msg, level=LogLevel.ERROR)
        elif bcp_str in linkdata:
            self.stats["bad"] += 1
            log_func(bcp_msg, level=LogLevel.ERROR)
            reload = False  # bad captcha same IP again

        return (ok, reload)

    def captcha_download_links_generator(self, solver: Type[CaptchaSolver], stop_event: threading.Event = None):
        """
            Generator for CAPTCHA download links using Tor sessions.
            Get download link by solving CAPTCHA, calls CAPTCHA related functions..

            Arguments:
                solver (CaptchaSolver): Class with solve method which gets CAPTCHA challenge URL and returns CAPTCHA answer
                stop_event: Threading event to check when to stop

            Returns:
                str: URL for downloading the file
        """

        self.numTorLinks = 0
        self.linkCache = LinkCache(path.join(self.temp_dir, self.filename))

        cached = self.linkCache.get()
        for link in cached:
            self.numTorLinks += 1
            yield link

        while (self.numTorLinks + self.alreadyDownloaded) < self.parts:
            if stop_event and stop_event.is_set():
                break

            self.tor.launch()  # ensure that TOR is running

            # reload tor after 1. use or all except badCaptcha case
            reload = False
            if self.stats["all"] > 0 or reload:
                self.tor.reload()

            try:
                s = requests.Session()
                s.proxies = self.tor.proxies
                if urlparse(self.url).hostname == "pornfile.cz":
                    r = s.post("https://pornfile.cz/porn-disclaimer/", data={
                        "agree": "Souhlasím",
                        "_do": "pornDisclaimer-submit",
                    })

                if self.needPassword:
                    s.get(self.url)  # to obtain initial set of cookies
                    s.post(self.url, data={
                        "password": self.password,
                        "password_send": "Odeslat",
                        "_do": "passwordProtectedForm-submit",
                    })

                resp = requests.Response()

                if self.isDirectDownload:
                    solver.log(f"TOR get downlink (timeout {self.conn_timeout})")
                    resp = s.get(self.captchaURL,
                                 headers=XML_HEADERS, timeout=self.conn_timeout)
                else:
                    solver.log(f"TOR get new CAPTCHA (timeout {self.conn_timeout})")
                    r = s.get(self.captchaURL, headers=XML_HEADERS)

                    # <img class="xapca-image" src="//xapca1.uloz.to/0fdc77841172eb6926bf57fe2e8a723226951197/image.jpg" alt="">
                    captcha_image_url = parse_single(
                        r.text, r'<img class="xapca-image" src="([^"]*)" alt="">')
                    if captcha_image_url is None:
                        solver.log("ERROR: Cannot parse CAPTCHA image URL from the page. Changing Tor circuit.", level=LogLevel.ERROR)
                        self.stats["all"] += 1
                        self.stats["net"] += 1
                        solver.stats(self.stats)
                        continue

                    captcha_data = {}
                    for name in ("_token_", "timestamp", "salt", "hash", "captcha_type", "_do"):
                        captcha_data[name] = parse_single(r.text, r'name="' + re.escape(name) + r'" value="([^"]*)"')

                    # https://github.com/setnicka/ulozto-downloader/issues/82
                    captcha_image_url = urljoin("https:", captcha_image_url)

                    solver.log("Image URL obtained, trying to solve")
                    captcha_answer = solver.solve(captcha_image_url, stop_event)

                    captcha_data["captcha_value"] = captcha_answer

                    solver.log(f"CAPTCHA answer '{captcha_answer}' (timeout {self.conn_timeout})")

                    resp = s.post(self.captchaURL, data=captcha_data,
                                  headers=XML_HEADERS, timeout=self.conn_timeout)

                # generate result or break
                result = self._link_validation_stat(resp, solver.log)
                solver.stats(self.stats)
                # for noreload (bad captcha no need reload TOR)

                if result[0]:
                    dlink = resp.json()["slowDownloadLink"]
                    # cache link here
                    self.linkCache.add(dlink)
                    self.numTorLinks += 1
                    yield dlink
                elif self.isDirectDownload:
                    solver.log("Direct download does no seem to work, trying with captcha resolution instead...")
                    self.isDirectDownload = False

            except requests.exceptions.ConnectionError:
                self._error_net_stat(
                    "Connection error, try new TOR session.", solver.log)
            except requests.exceptions.ChunkedEncodingError:
                self._error_net_stat(
                    "Error while communicating over Tor, try new TOR session", solver.log)
            except requests.exceptions.ReadTimeout:
                self._error_net_stat(
                    "ReadTimeout error, try new TOR session.", solver.log)

            solver.stats(self.stats)

    def enter_password(self, session):

        if not self.password and not self.frontend.supports_prompt:
            raise ValueError("The file requires a password. Provide it by re-running with '--password <password>'.")

        while True:
            if not self.password:
                self.password = self.frontend.prompt("File is password-protected, enter the password: ", level=LogLevel.WARNING)

            r = session.post(
                self.url,
                data={
                    "password": self.password,
                    "password_send": "Odeslat",
                    "_do": "passwordProtectedForm-submit",
                }
            )

            # Accept the password and store (auth) cookies
            if r.status_code == 200:
                print("Password accepted.")
                return r

            # Wrong password - retry when using frontend with prompt
            if self.frontend.supports_prompt:
                self.frontend.main_log("Wrong password, try again", level=LogLevel.ERROR)
                self.password = None
                continue

            raise ValueError("Wrong password")
