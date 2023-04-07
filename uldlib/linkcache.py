import os
from time import time
from urllib.parse import parse_qs

from .const import CACHEPOSTFIX


class LinkCache:
    """
    A class for caching download links.

    Attributes:
        filename (str): The name of the file where the links will be stored.
        shorten_validity (int, optional): number of seconds of witch shorten the validity of given link.

    Methods:
        delete_cache_file: Deletes the cache file if it exists.
        add: Adds a new link to the cache.
        get_all_valid_links: Returns all valid links from the cache.
        _is_link_valid: Determines whether a link is valid based on its timestamp query parameter.
        _get_cache_content: Returns the content of the cache file.
    """

    def __init__(self, filename: str, shorten_validity: int = 5):
        """
        Initializes a new instance of the LinkCache class.

        Args:
            filename (str): The name of the file where the links will be stored.
            shorten_validity (int, optional): number of seconds of witch shorten the validity of given link.
        """
        self.filename = filename
        self.cache_file = self.filename + CACHEPOSTFIX
        self.shorten_validity = shorten_validity

    def delete_cache_file(self) -> None:
        """
        Deletes the cache file if it exists.
        """
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)

    def add(self, link: str) -> None:
        """
        Adds a new link to the cache.
        """
        with open(self.cache_file, 'a') as cache:
            cache.write(f"{link}\n")

    def get_all_valid_links(self) -> list[str]:
        """
        Returns all valid links from the cache.
        """
        cache_content = self._get_cache_content()
        return [link for link in cache_content if self._is_link_valid(link)]

    def _is_link_valid(self, link: str) -> bool:
        """
        Determines whether a link is valid based on its timestamp query parameter.
        """
        query_string = parse_qs(link, separator=';')
        if not query_string.get("tm"):
            # link does not contain 'tm' query parameter
            # therefore is not valid
            return False
        link_timestamp = int(query_string.get("tm")[0])
        time_now = int(time())
        # flag link as invalid {shorten_validity} second before it actually expires
        return time_now < (link_timestamp - self.shorten_validity)

    def _get_cache_content(self) -> list[str]:
        """
        Returns the content of the cache file.
        """
        if not os.path.exists(self.cache_file):
            return []
        with open(self.cache_file, 'r') as cache:
            return cache.readlines()
