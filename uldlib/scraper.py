from __future__ import annotations

import re

from uldlib.exceptions import ScrapingError


class FileMetadataScraper:

    FILENAME_REGEX = r'<title>([^\|]*)\s+\|.*</title>'
    QUICK_DOWNLOAD_REGEX = r'href="(/quickDownload/[^"]*)"'
    DIRECT_DOWNLOAD_REGEX = r'data-href="/download-dialog/free/[^"]+" +class=".+(js-free-download-button-direct).+"'
    CAPTCHA_URL_REGEX = r'data-href="(/download-dialog/free/[^"]*)"'

    def __init__(self, html_doc: str) -> None:
        self.html_doc = html_doc

    def _get_match_or_none(self, regex: str) -> None | str:
        regex_pattern = re.compile(regex, re.IGNORECASE)
        results = regex_pattern.findall(self.html_doc)
        if len(results) == 0:
            return None
        return results[0]

    @property
    def filename(self) -> str:
        filename = self._get_match_or_none(self.FILENAME_REGEX)
        if not filename:
            raise ScrapingError("cannot get filename")
        # Replace illegal characters in filename
        # https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file
        return re.sub(r'[<>:,\"/\\|\?*]', "-", filename)

    @property
    def is_direct_download(self) -> bool:
        direct_download_url = self._get_match_or_none(self.DIRECT_DOWNLOAD_REGEX)
        return direct_download_url is not None

    @property
    def quick_download_url(self) -> str:
        return self._get_match_or_none(self.QUICK_DOWNLOAD_REGEX)

    @property
    def captcha_url(self) -> str:
        captcha_url = self._get_match_or_none(self.CAPTCHA_URL_REGEX)
        if not captcha_url:
            raise ScrapingError("Cannot get captcha URL")
        return captcha_url
