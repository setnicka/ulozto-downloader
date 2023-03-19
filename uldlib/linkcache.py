import os
from time import time
from urllib.parse import parse_qs

from .const import CACHEPOSTFIX


class LinkCache:
    """
    Arguments:
        filename (str): path to save downloaded file
        shorten_validity (int): number of seconds of witch shorten the validity of given link
    """

    def __init__(self, filename: str, shorten_validity: int = 5):
        self.filename = filename
        self.cache_file = self.filename + CACHEPOSTFIX
        self.shorten_validity = shorten_validity

    def delete_cache_file(self) -> None:
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)

    def add(self, link: str) -> None:
        """add new link to cache"""
        with open(self.cache_file, 'a') as cache:
            cache.write(f"{link}\n")

    def _get_cache_content(self) -> list[str]:
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as cache:
                return cache.readlines()
        return []

    def get_all_valid_links(self) -> list[str]:
        """Returns only valid links from the cache"""
        cache_content = self._get_cache_content()
        return [link for link in cache_content if self._is_link_valid(link)]

    def _is_link_valid(self, link: str) -> bool:
        query_string = parse_qs(link, separator=';')
        if not query_string.get("tm"):
            # link does not contain 'tm' query parameter
            # therefore is not valid
            return False
        link_timestamp = int(query_string.get("tm")[0])
        time_now = int(time())
        # flag link as invalid {shorten_validity} second before it actually expires
        return time_now < (link_timestamp - self.shorten_validity)
