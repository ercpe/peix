# -*- coding: utf-8 -*-
import os
from io import BytesIO
from unittest import mock

from peix.format import EixFileFormat


class BytesMock(object):

    def __init__(self, buff):
        self.buff = BytesIO(buff)

    def read(self, fd, n):
        return self.buff.read(n)

    def lseek(self, fd, pos, where):
        return self.buff.seek(pos, where)

    def __getattr__(self, item):
        return getattr(os, item)


class TestFormat(object):
    
    def test_read_number(self):

        for raw_bytes, num in [
            (b'\x00', 0),
            (b'\x01', 1),
            (b'\xfe', 254),
            (b'\xff\x00', 255),
            (b'\xff\x01\x00', 256),
            (b'\xff\x01\xff', 511),
            (b'\xff\xfe\xff', 65279),
            (b'\xff\xff\x00\x00', 65280),
            (b'\xff\xff\x00\x01', 65281),
            (b'\xff\xff\x01\x00\x00', 65536),
            (b'\xff\xff\xab\xcd\xef', 11259375),
            (b'\xff\xff\xff\x00\xab\xcd', 16755661),
            (b'\xff\xff\xff\x01\xab\xcd\xef', 28036591),
        ]:
            with mock.patch('peix.format.os', new=BytesMock(raw_bytes)):
                eff = EixFileFormat()
                assert eff.read_number() == num
