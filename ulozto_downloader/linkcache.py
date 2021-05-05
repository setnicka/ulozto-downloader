import re
from time import time


class LinkCache:
    def __init__(self, filename, invtime=7200):
        self.filename = filename
        self.invtime = invtime
        self.filename = filename

    def add(self, link):
        with open(self.filename, 'a+') as f:
            if self.validate(link):
                f.write(f"{link}\n")

    def get_all(self):
        with open(self.filename, 'r') as f:
            return f.readlines()

    def set_all(self, lines):
        with open(self.filename, 'w') as f:
            f.writelines(lines)

    def validate(self, link):
        p = re.compile('[^;]+;tm=([0-9]+);')
        tst = p.findall(link)
        if len(tst) > 0:
            ts = int(tst[0])
            tn = int(time())
            if (ts - tn) <= self.invtime:
                return False
            else:
                return True
        else:
            return False

    def invalidate(self):
        lines = self.get_all()
        validated = []
        while len(lines) > 0:
            link = lines.pop()
            if self.validate(link):
                validated.insert(len(validated), link)

        self.set_all(validated)

    def get(self, idx):
        lines = self.get_all()
        if idx > len(lines) - 1:
            return False

        link = lines.pop(idx)
        if self.validate(link):
            return link
        else:
            self.invalidate()
            return False
