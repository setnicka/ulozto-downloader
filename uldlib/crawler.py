import re
from urllib.parse import urlparse

import requests


class UloztoCrawler:

    ERRORS = {
        451: "File was deleted due to legal reasons (status code 451)",
        404: "File Not Found"
    }

    def __init__(self, url: str):
        self._url = url
        self.cookies = None

    @property
    def url(self) -> str:
        # strip url of tracking part
        # eg. #!ZGHmLmR2ZzR0MQx2MGN4MJV1MzV0ASH4H3DlH3yXFUuvpJIyMD==
        stripped_url = urlparse(self._url.split("#")[0])
        if not stripped_url.hostname:
            raise Exception("Invalid URL")
        if not stripped_url.scheme:
            stripped_url.scheme = "https"
        self._url = "{uri.scheme}://{uri.netloc}{uri.path}".format(uri=stripped_url)
        return self._url

    @property
    def slug(self) -> str:
        match = re.search(r'/file/([^\\]*)/', self.url)
        if not match:
            raise Exception("No Slug was found")
        return match.group(1)

    def _submit_disclaimer(self) -> None:
        disclaimer_url = "https://pornfile.cz/porn-disclaimer/"
        data = {
            "agree": "Souhlasím",
            "_do": "pornDisclaimer-submit"
        }
        response = requests.post(disclaimer_url, data=data)
        if response.status_code != 200:
            raise Exception(self.ERRORS.get(response.status_code, "GET request failed"))
        self.cookies = response.cookies

    def get_html_document(self) -> str:
        # special case for Pornfile.cz run by Uloz.to - confirmation is needed
        if "pornfile.cz" in self.url:
            self._submit_disclaimer()
        response = requests.get(self.url, cookies=self.cookies)
        if response.status_code != 200:
            raise Exception(self.ERRORS.get(response.status_code, "GET request failed"))
        return response.text
