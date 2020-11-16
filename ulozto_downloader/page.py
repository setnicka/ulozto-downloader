import re
import time
from urllib.parse import urlparse
import requests

from .const import XML_HEADERS

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
            raise RuntimeError("File was deleted from Uloz.to due to legal reasons (status code 451)")
        elif r.status_code != 200:
            raise RuntimeError(f"Uloz.to returned status code {r.status_code}, file does not exist")

        # Get file slug from URL
        self.slug = parse_single(parsed_url.path, r'/file/([^\\]*)/')
        if self.slug is None:
            raise RuntimeError("Cannot parse file slug from Uloz.to URL")

        self.body = r.text

    def parse(self):
        """Try to parse all information from the Uloz.to page (filename, download links, ...)

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
            raise RuntimeError("Cannot parse Uloz.to page to get download information, no direct download URL and no CAPTCHA challenge URL found")

    def get_captcha_download_link(self, captcha_solve_func, print_func=print):
        """Get download link by solving CAPTCHA, calls CAPTCHA related functions.

            Arguments:
                captcha_solve_func (func): Function which gets CAPTCHA challenge URL and returns CAPTCHA answer
                print_func (func): Function used for printing log (default is bultin 'print')

            Returns:
                str: URL for downloading the file
        """

        print_func("CAPTCHA image challenge...")
        while True:
            captcha_image, captcha_data, cookies = self.get_new_captcha()
            captcha_answer = captcha_solve_func(captcha_image, print_func=print_func)
            # print_func("CAPTCHA input from user: {}".format(captcha_answer))

            captcha_data["captcha_value"] = captcha_answer
            response = requests.post(self.captchaURL, data=captcha_data, headers=XML_HEADERS, cookies=cookies)
            response = response.json()

            if "slowDownloadLink" in response:
                return response["slowDownloadLink"]

            if "/download-dialog/free/limit-exceeded" in str(response):
                # {"redirectDialogContent": "/download-dialog/free/limit-exceeded?fileSlug=5USLDPenZ&repeated=0"}
                # 1 minute pause is required between requests
                for i in range(60, 0, -1):
                    print_func("Blocked by Uloz.to download limit. Retrying in {} seconds.".format(i))
                    time.sleep(1)
                continue

            print_func("Wrong CAPTCHA input '{}', try again...".format(captcha_answer))

    def get_new_captcha(self):
        """Get CAPTCHA url and form parameters from given page.

            Arguments:
                url (str): URL of the CAPTCHA challenge form

            Returns:
                str: URL of the CAPTCHA image
                dict: Parsed JSON with parameters of the CAPTCHA
                RequestsCookieJar: Obtained cookies from the page
        """

        cookies = None
        # special case for Pornfile.cz run by Uloz.to - confirmation is needed
        if urlparse(self.url).hostname == "pornfile.cz":
            r = requests.post("https://pornfile.cz/porn-disclaimer/", data={
                "agree": "Souhlasím",
                "_do": "pornDisclaimer-submit",
            })
            cookies = r.cookies

        r = requests.get(self.captchaURL, cookies=cookies)

        # <img class="xapca-image" src="//xapca1.uloz.to/0fdc77841172eb6926bf57fe2e8a723226951197/image.jpg" alt="">
        captcha_image = parse_single(r.text, r'<img class="xapca-image" src="([^"]*)" alt="">')
        if captcha_image is None:
            raise RuntimeError("Cannot get CAPTCHA image URL")

        captcha_data = {}
        for name in ("_token_", "timestamp", "salt", "hash", "captcha_type", "_do"):
            captcha_data[name] = parse_single(r.text, r'name="' + re.escape(name) + r'" value="([^"]*)"')

        return "https:" + captcha_image, captcha_data, r.cookies
