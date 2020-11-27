import re
from urllib.parse import urlparse
import requests
import logging
import ssl

from .const import XML_HEADERS

from requests.sessions import RequestsCookieJar
from torpy.http.requests import tor_requests_session

# disable warnings and below from torpy
logging.getLogger('torpy').setLevel(logging.ERROR)


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

    def __init__(self, url):
        """Check given url and if it looks ok GET the Uloz.to page and save it.

            Arguments:
                url (str): URL of the page with file

            Raises:
                RuntimeError: On invalid URL, deleted file or other error related to getting the page.
        """

        self.url = url
        parsed_url = urlparse(url)
        self.pagename = parsed_url.hostname.capitalize()

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
            raise RuntimeError(f"File was deleted from {self.pagename} due to legal reasons (status code 451)")
        elif r.status_code != 200:
            raise RuntimeError(f"{self.pagename} returned status code {r.status_code}, file does not exist")

        # Get file slug from URL
        self.slug = parse_single(parsed_url.path, r'/file/([^\\]*)/')
        if self.slug is None:
            raise RuntimeError(f"Cannot parse file slug from {self.pagename} URL")

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

        # Some files may be download without CAPTCHA, there is special URL on the parsed page:
        # a) <a ... href="/slowDownload/E7jJsmR2ix73">...</a>
        self.slowDownloadURL = parse_single(self.body, r'href="(/slowDownload/[^"]*)"')
        if self.slowDownloadURL:
            download_found = True
            self.slowDownloadURL = self.baseURL + self.slowDownloadURL
        # b) <a ... href="/quickDownload/E7jJsmR2ix73">...</a>
        self.quickDownloadURL = parse_single(self.body, r'href="(/quickDownload/[^"]*)"')
        if self.quickDownloadURL:
            download_found = True
            self.quickDownloadURL = self.baseURL + self.quickDownloadURL

        # Other files are protected by CAPTCHA challenge
        # <a href="javascript:;" data-href="/download-dialog/free/default?fileSlug=apj0q49iETRR" class="c-button c-button__c-white js-free-download-button-dialog t-free-download-button">
        self.captchaURL = parse_single(self.body, r'data-href="(/download-dialog/free/[^"]*)"')
        if self.captchaURL:
            download_found = True
            self.captchaURL = self.baseURL + self.captchaURL

        # Check if slowDirectDownload or form data for CAPTCHA was parsed
        if not download_found:
            raise RuntimeError(f"Cannot parse {self.pagename} page to get download information,"
                               + " no direct download URL and no CAPTCHA challenge URL found")

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

        while True:
            print_func("Opening new Tor circuit (may take some time)...")
            try:
                with tor_requests_session(hops_count=2, retries=0) as s:
                    print_func("Tor connection established, solving CAPTCHA...")

                    if urlparse(self.url).hostname == "pornfile.cz":
                        r = s.post("https://pornfile.cz/porn-disclaimer/", data={
                            "agree": "Souhlasím",
                            "_do": "pornDisclaimer-submit",
                        })

                    while True:
                        r = s.get(self.captchaURL, allow_redirects=False)

                        if r.status_code == 302:
                            # we got download URL without solving CAPTCHA, be happy
                            yield r.headers["location"]
                            break  # from each Tor connection use only one download link to avoid 429 Too Many Connections

                        if "/download-dialog/free/limit-exceeded" in str(r.text):
                            print_func(f"Blocked by {self.pagename} download limit (before getting CAPTCHA). Changing Tor circuit.")
                            break

                        # <img class="xapca-image" src="//xapca1.uloz.to/0fdc77841172eb6926bf57fe2e8a723226951197/image.jpg" alt="">
                        captcha_image_url = parse_single(r.text, r'<img class="xapca-image" src="([^"]*)" alt="">')
                        if captcha_image_url is None:
                            print_func("ERROR: Cannot parse CAPTCHA image URL from the page. Changing Tor circuit.")
                            break

                        captcha_data = {}
                        for name in ("_token_", "timestamp", "salt", "hash", "captcha_type", "_do"):
                            captcha_data[name] = parse_single(r.text, r'name="' + re.escape(name) + r'" value="([^"]*)"')

                        print_func("Image URL obtained, trying to solve")
                        captcha_answer = captcha_solve_func("https:" + captcha_image_url, print_func=print_func)
                        # print_func("CAPTCHA input from user: {}".format(captcha_answer))
                        captcha_data["captcha_value"] = captcha_answer
                        response = s.post(self.captchaURL, data=captcha_data, headers=XML_HEADERS)
                        response = response.json()

                        if "slowDownloadLink" in response:
                            yield response["slowDownloadLink"]
                            break  # from each Tor connection use only one download link to avoid 429 Too Many Connections

                        if "/download-dialog/free/limit-exceeded" in str(response):
                            print_func(f"Blocked by {self.pagename} download limit. Changing Tor circuit.")
                            break

                        print_func("Wrong CAPTCHA input '{}', try again...".format(captcha_answer))
            except requests.exceptions.ConnectionError:
                print_func("Connection error, trying new Tor circuit")
            except requests.exceptions.ChunkedEncodingError:
                print_func("Error while communicating over Tor, trying new Tor circuit")
            except requests.exceptions.ReadTimeout:
                print_func("ReadTimeout error, maybe not working Tor circuit, trying new Tor circuit")
            except ssl.SSLError:
                # Error raised on exit, just ignore it
                return
