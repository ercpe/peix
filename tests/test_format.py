# -*- coding: utf-8 -*-
import os
from io import BytesIO
from unittest import mock

import binascii

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

        self._test_read_number(b'\x00', 0)
        self._test_read_number(b'\x01', 1)
        self._test_read_number(b'\xfe', 254)
        self._test_read_number(b'\xff\x00', 255)
        self._test_read_number(b'\xff\x01\x00', 256)
        self._test_read_number(b'\xff\x01\xff', 511)
        self._test_read_number(b'\xff\xfe\xff', 65279)
        self._test_read_number(b'\xff\xff\x00\x00', 65280)
        self._test_read_number(b'\xff\xff\x00\x01', 65281)
        self._test_read_number(b'\xff\xff\x01\x00\x00', 65536)
        self._test_read_number(b'\xff\xff\xab\xcd\xef', 11259375)
        self._test_read_number(b'\xff\xff\xff\x00\xab\xcd', 16755661)
        self._test_read_number(b'\xff\xff\xff\x01\xab\xcd\xef', 28036591)

    def _test_read_number(self, raw_bytes, expected_number):
        # junk is used to avoid false asserts because .read(n) reads *at most* n bytes and doesn't complain
        # if fewer bytes are read
        junk = b'\x01' * 20

        print("read_number - bytes: %s, expected: %s" % (binascii.hexlify(raw_bytes), expected_number))
        with mock.patch('peix.format.os', new=BytesMock(raw_bytes + junk)):
            assert EixFileFormat().read_number() == expected_number