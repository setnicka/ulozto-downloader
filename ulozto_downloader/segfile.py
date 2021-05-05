import math
import colors
from . import utils, const
import os
from io import BytesIO
from sys import byteorder
from collections import UserDict


class SegFileWriter:
    """Implementation segment write file"""

    def __init__(self, file, parts, seg_idx):
        self.file = file
        self.parts = parts
        self.id = seg_idx
        self.open()

    def open(self):
        self.fp = open(self.file, 'rb+')
        self._load_stat()

    def _load_stat(self):
        # open stat file - must exists
        self.sfp = open(self.file + const.SPREFIX, 'rb+')
        # byte size of stat segment
        self.sbs = int.from_bytes(self.sfp.read(1), byteorder)
        # total_size
        self.total_size = int.from_bytes(self.sfp.read(self.sbs), byteorder)

        # size
        self.size = math.ceil(self.total_size / self.parts)

        # from, to, size
        self.pfrom = self.size * self.id
        self.pto = min(((self.size * (self.id + 1)) - 1), self.total_size)

        # fix last part have different size
        if self.id == (self.parts - 1):
            self.size = self.total_size - self.pfrom

        # get downloaded
        self.stat_pos = 1 + self.sbs + (self.id * self.sbs)
        self.sfp.seek(self.stat_pos, os.SEEK_SET)
        self.cur_pos = int.from_bytes(self.sfp.read(self.sbs), byteorder)
        self.downloaded = self.cur_pos - self.pfrom

        # seek file position
        self.fp.seek(self.cur_pos, os.SEEK_SET)

    def _write_stat(self, newpos):
        self.sfp.seek(self.stat_pos, os.SEEK_SET)
        self.sfp.write(newpos.to_bytes(self.sbs, byteorder))
        self.sfp.flush()  # write to file

    def write(self, chunk):
        self.fp.seek(self.cur_pos, os.SEEK_SET)
        wrt = self.fp.write(chunk)
        self.downloaded += wrt
        self.cur_pos += wrt
        self._write_stat(self.cur_pos)


class SegFileLoader:
    def __init__(self, filename, size, parts):
        self.filename = filename
        self.size = size
        self.parts = parts
        self._first_created = False
        # create stat file if not exists
        self._create_files_if_not_ex()

    def make_writers(self):
        if self._first_created:
            self.fp.close()
            self.sfp.close()
            parts = self.parts
        else:
            parts = self._get_parts_from_existing()
        return [
            SegFileWriter(self.filename, parts, i)
            for i in range(parts)
        ]

    def _get_parts_from_existing(self):
        self.sfp = open(self.filename + const.SPREFIX, 'rb')
        sbs = int.from_bytes(self.sfp.read(1), byteorder)
        size = int.from_bytes(self.sfp.read(sbs), byteorder)

        parts_bytes_remain = self.sfp.read()  # read bytes remain
        parts = int(len(parts_bytes_remain) / sbs)
        self.part_size = math.ceil(size / parts)
        self.sfp.close()

        # if file size not match is not same file - truncate to fresh new
        if self.size != size:
            self._create_files_if_not_ex()
            return self.parts
        else:
            return parts

    def _create_files_if_not_ex(self):
        if not os.path.isfile(self.filename + const.SPREFIX):
            self.fp = open(self.filename, 'wb+')
            self.fp.truncate(self.size)
            self.sfp = open(self.filename + const.SPREFIX, 'wb+')

            self._make_stat_file_data(self.size, self.parts)
            self._first_created = True

    def _make_stat_file_data(self, size, parts):
        self.part_size = math.ceil(size / parts)
        sb_size = math.ceil(size.bit_length() / 8) + 1

        self.sfp.write(sb_size.to_bytes(1, byteorder))
        self.sfp.write(size.to_bytes(sb_size, byteorder))

        for i in range(parts):
            stat_pos = 1 + sb_size + (i * sb_size)
            self.sfp.seek(stat_pos, os.SEEK_SET)
            seg = (i * self.part_size).to_bytes(sb_size, byteorder)
            self.sfp.write(seg)
