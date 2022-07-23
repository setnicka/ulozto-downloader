import re
from urllib.parse import urlparse
from os import path, remove
import sys
import requests
import colors

from .const import XML_HEADERS
from .linkcache import LinkCache

from requests.sessions import RequestsCookieJar


def parse_single(text, regex):
    p = re.compile(regex, re.IGNORECASE)
    result = p.findall(text)
    if len(result) == 0:
        return None
    return result[0]


class Page:
    url: str
    body: str
    cookies: RequestsCookieJar
    baseURL: str
    slug: str
    pagename: str

    filename: str
    slowDownloadURL: str
    quickDownloadURL: str
    captchaURL: str
    isDirectDownload: bool
    numTorLinks: int
    alreadyDownloaded: int

    def __init__(self, url, target_dir, parts, tor):
        """Check given url and if it looks ok GET the Uloz.to page and save it.

            Arguments:
                url (str): URL of the page with file
                target_dir (str): user defined output directory
                parts (int): number of segments (parts)
                tor: (TorRunner): tor runner instance
            Raises:
                RuntimeError: On invalid URL, deleted file or other error related to getting the page.
        """

        self.url = url
        self.target_dir = target_dir
        self.parts = parts
        self.tor = tor
        parsed_url = urlparse(url)
        self.pagename = parsed_url.hostname.capitalize()
        self.cli_initialized = False
        self.alreadyDownloaded = 0
        self.stats = {"all": 0, "ok": 0, "bad": 0,
                      "lim": 0, "block": 0, "net": 0}  # statistics

        cookies = None
        # special case for Pornfile.cz run by Uloz.to - confirmation is needed
        if parsed_url.hostname == "pornfile.cz":
            r = requests.post("https://pornfile.cz/porn-disclaimer/", data={
                "agree": "Souhlasím",
                "_do": "pornDisclaimer-submit",
            })
            cookies = r.cookies

        # If file is file-tracking link we need to get normal file link from it
        if url.startswith('{uri.scheme}://{uri.netloc}/file-tracking/'.format(uri=parsed_url)):
            r = requests.get(url, allow_redirects=False, cookies=cookies)
            if 'Location' in r.headers:
                self.url = r.headers['Location']
                parsed_url = urlparse(self.url)

        r = requests.get(self.url, cookies=cookies)
        self.baseURL = "{uri.scheme}://{uri.netloc}".format(uri=parsed_url)

        if r.status_code == 451:
            raise RuntimeError(
                f"File was deleted from {self.pagename} due to legal reasons (status code 451)")
        elif r.status_code != 200:
            raise RuntimeError(
                f"{self.pagename} returned status code {r.status_code}, file does not exist")

        # Get file slug from URL
        self.slug = parse_single(parsed_url.path, r'/file/([^\\]*)/')
        if self.slug is None:
            raise RuntimeError(
                f"Cannot parse file slug from {self.pagename} URL")

        self.body = r.text

    def parse(self):
        """Try to parse all information from the page (filename, download links, ...)

        Raises:
            RuntimeError: When mandatory fields cannot be parsed.
        """

        # Parse filename only to the first | (Uloz.to sometimes add titles like "name | on-line video | Ulož.to" and so on)
        self.filename = parse_single(self.body, r'<title>([^\|]*)\s+\|.*</title>')

        # Replace illegal characters in filename https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file
        self.filename = re.sub(r'[<>:,\"/\\|\?*]', "-", self.filename)

        download_found = False

        self.quickDownloadURL = parse_single(self.body, r'href="(/quickDownload/[^"]*)"')
        if self.quickDownloadURL:
            download_found = True
            self.quickDownloadURL = self.baseURL + self.quickDownloadURL

        # detect direct download from self.body
        isDirect = parse_single(
            self.body, r'data-href="/download-dialog/free/[^"]+" +class=".+(js-free-download-button-direct).+"')

        if isDirect == 'js-free-download-button-direct':
            self.isDirectDownload = True
        else:
            self.isDirectDownload = False

        # Other files are protected by CAPTCHA challenge
        # <a href="javascript:;" data-href="/download-dialog/free/default?fileSlug=apj0q49iETRR" class="c-button c-button__c-white js-free-download-button-dialog t-free-download-button">
        self.captchaURL = parse_single(self.body, r'data-href="(/download-dialog/free/[^"]*)"')
        if self.captchaURL:
            download_found = True
            self.captchaURL = self.baseURL + self.captchaURL
        self.slowDownloadURL = self.captchaURL

        # Check if slowDirectDownload or form data for CAPTCHA was parsed
        if not download_found:
            raise RuntimeError(f"Cannot parse {self.pagename} page to get download information,"
                               + " no direct download URL and no CAPTCHA challenge URL found")

    def _stat_fmt(self):
        count = colors.blue(self.stats['all'])
        ok = colors.green(self.stats['ok'])
        bad = colors.red(self.stats['bad'])
        lim = colors.red(self.stats['lim'])
        blo = colors.red(self.stats['block'])
        net = colors.red(self.stats['net'])
        return f":) [Ok: {ok} / {count}] :( [Badcp: {bad} Limited: {lim} Censored: {blo} NetErr: {net}]"

    # print TOR network error and += stats
    def _error_net_stat(self, err, print_func):
        self.stats["all"] += 1
        print_func(colors.red(f"Network error get new TOR connection: {err}"))
        self.stats["net"] += 1

    def _link_validation_stat(self, resp, print_func):
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
                print_func(colors.red(lim_msg))
        elif blk_str in linkdata:
            self.stats["block"] += 1
            if not self.isDirectDownload:
                print_func(colors.red(blk_msg))
        elif bcp_str in linkdata:
            self.stats["bad"] += 1
            print_func(colors.red(bcp_msg))
            reload = False  # bad captcha same IP again

        return (ok, reload)

    def _captcha_send_print_stat(self, answ, print_func):
        print_func(f"Send CAPTCHA:  '{answ}' {self._stat_fmt()}")

    def captcha_download_links_generator(self, captcha_solve_func, print_func=print):
        """
            Generator for CAPTCHA download links using Tor sessions.
            Get download link by solving CAPTCHA, calls CAPTCHA related functions..

            Arguments:
                captcha_solve_func (func): Function which gets CAPTCHA challenge URL and returns CAPTCHA answer
                print_func (func): Function used for printing log (default is bultin 'print')

            Returns:
                str: URL for downloading the file
        """

        self.numTorLinks = 0
        self.torRunning = False
        self.cacheEmpty = False
        self.linkCache = LinkCache(path.join(self.target_dir, self.filename))

        while not self.cacheEmpty:
            cached = self.linkCache.get()
            self.cacheEmpty = True
            for link in cached:
                # linkCache.use(self.numTorLinks)
                self.numTorLinks += 1
                yield link

        while (self.numTorLinks + self.alreadyDownloaded) < self.parts:
            if not self.torRunning:
                print("Starting TOR...")
                # tor started after cli initialized
                try:
                    self.tor.start(
                        cli_initialized=self.cli_initialized, parts=self.parts)
                    self.torRunning = True
                    proxies = {
                        'http': 'socks5://127.0.0.1:' + str(self.tor.tor_ports[0]),
                        'https': 'socks5://127.0.0.1:' + str(self.tor.tor_ports[0])
                    }

                except OSError as e:
                    self._error_net_stat(
                        f"Tor start failed: {e}, exiting.. try run program again..", print_func)
                    # remove tor data
                    if path.exists(self.tor.ddir):
                        remove(self.tor.ddir)
                    sys.exit(1)

            # reload tor after 1. use or all except badCatcha case
            reload = False
            if self.stats["all"] > 0 or reload:
                self.tor.reload()

            try:
                s = requests.Session()
                if urlparse(self.url).hostname == "pornfile.cz":
                    r = s.post("https://pornfile.cz/porn-disclaimer/", data={
                        "agree": "Souhlasím",
                        "_do": "pornDisclaimer-submit",
                    })

                resp = requests.Response()

                if self.isDirectDownload:
                    print_func(
                        f"New TOR session for GET downlink {self._stat_fmt()}")
                    resp = s.get(self.captchaURL,
                                 headers=XML_HEADERS, proxies=proxies)
                else:
                    print_func(
                        f"New TOR session for POST captcha {self._stat_fmt()}")
                    r = s.get(self.captchaURL, headers=XML_HEADERS)

                    # <img class="xapca-image" src="//xapca1.uloz.to/0fdc77841172eb6926bf57fe2e8a723226951197/image.jpg" alt="">
                    captcha_image_url = parse_single(
                        r.text, r'<img class="xapca-image" src="([^"]*)" alt="">')
                    if captcha_image_url is None:
                        print_func(
                            "ERROR: Cannot parse CAPTCHA image URL from the page. Changing Tor circuit.")
                        self.stats["all"] += 1
                        self.stats["net"] += 1
                        reload = True
                        continue

                    captcha_data = {}
                    for name in ("_token_", "timestamp", "salt", "hash", "captcha_type", "_do"):
                        captcha_data[name] = parse_single(r.text, r'name="' + re.escape(name) + r'" value="([^"]*)"')

                    print_func("Image URL obtained, trying to solve")
                    captcha_answer = captcha_solve_func(
                        "https:" + captcha_image_url, print_func=print_func)

                    captcha_data["captcha_value"] = captcha_answer

                    self._captcha_send_print_stat(
                        captcha_answer, print_func)
                    resp = s.post(self.captchaURL, data=captcha_data,
                                  headers=XML_HEADERS, proxies=proxies)

                # generate result or break
                result = self._link_validation_stat(resp, print_func)
                # for noreload (bad captcha no need reload TOR)
                reload = result[1]
                if result[0]:
                    dlink = resp.json()["slowDownloadLink"]
                    # cache link here
                    self.linkCache.add(dlink)
                    self.numTorLinks += 1
                    yield dlink

            except requests.exceptions.ConnectionError:
                self._error_net_stat(
                    "Connection error, try new TOR session.", print_func)
            except requests.exceptions.ChunkedEncodingError:
                self._error_net_stat(
                    "Error while communicating over Tor, try new TOR session", print_func)
            except requests.exceptions.ReadTimeout:
                self._error_net_stat(
                    "ReadTimeout error, try new TOR session.", print_func)
