from os import path, remove
from math import ceil
from time import time
import re
from .const import CACHEPOSTFIX


class LinkCache:
    """
    Arguments:
        filename (str): path to save downloaded file
        invsec (int): number of seconds before link timeout
            (tm=<ddddddddddd> timestamp), that make link invalid
    """

    def __init__(self, filename, invsec=5):
        self.filename = filename
        self.cachefile = self.filename + CACHEPOSTFIX
        self.invsec = invsec

    def add(self, link):
        """add new link to cache and add usage index (set to 1)"""
        # if path.exists(self.cachefile):
        with open(self.cachefile, 'a') as cache:
            cache.write(f"{link}\n")

    def _get_all(self):
        if path.exists(self.cachefile):
            with open(self.cachefile, 'r') as cache:
                return cache.readlines()
        else:
            return []

    def get(self):
        """Get all links from cache and invalidate before return"""
        if path.exists(self.cachefile):
            self.invalidion()
            full_cache = self._get_all()
            return full_cache
        else:
            return []

    def validate(self, link):
        valid = False
        tsr = re.compile(';tm=([^;]+);')
        ts = tsr.findall(link)
        if len(ts) > 0:
            tnow_sec = ceil(time())
            tst = int(ts[0])
            if (tnow_sec < (tst - self.invsec)):
                valid = True
        return valid

    def invalidion(self):
        full_cache = self._get_all()
        if len(full_cache) > 0:
            invcache = []
            for link in full_cache:
                valid = self.validate(link)
                if valid:
                    invcache.append(link)
            if len(invcache) < len(full_cache):
                remove(self.cachefile)
                for link in invcache:
                    # already contains '\n' prevent duplicity
                    self.add(link.strip('\n'))
