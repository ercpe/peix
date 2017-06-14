# -*- coding: utf-8 -*-
import os
from io import BytesIO
from unittest import mock

import binascii

import pytest

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

# junk is used to avoid false asserts because .read(n) reads *at most* n bytes and doesn't complain
# if fewer bytes are read
junk = b'\x01' * 20

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

        print("read_number - bytes: %s, expected: %s" % (binascii.hexlify(raw_bytes), expected_number))
        with mock.patch('peix.format.os', new=BytesMock(raw_bytes + junk)):
            assert EixFileFormat().read_number() == expected_number

    def test_read_string(self):
        
        # str of len 0
        with mock.patch('peix.format.os', new=BytesMock(b'\x00' + junk)):
            assert EixFileFormat().read_string() == ''

        # str of len 3
        with mock.patch('peix.format.os', new=BytesMock(b'\x03abc' + junk)):
            assert EixFileFormat().read_string() == 'abc'

    def test_read_vector(self):

        # empty vector
        with mock.patch('peix.format.os', new=BytesMock(b'\x00' + junk)):
            eff = EixFileFormat()
            assert eff.read_vector(eff.read_string) == []
        
        # vector with one element (3 bytes string)
        b = b'\x01\x01\x01'
        with mock.patch('peix.format.os', new=BytesMock(b + junk)):
            eff = EixFileFormat()
            assert eff.read_vector(eff.read_number) == [1]

    def test_read_hash(self):
        # empty vector
        with mock.patch('peix.format.os', new=BytesMock(b'\x00' + junk)):
            eff = EixFileFormat()
            assert eff.read_vector(eff.read_string) == []

        # vector with one element (3 bytes string)
        b = b'\x01\x03abc'
        with mock.patch('peix.format.os', new=BytesMock(b + junk)):
            eff = EixFileFormat()
            assert eff.read_vector(eff.read_string) == ['abc']

    def test_read_hashed_string(self):
        l = ['foo', 'bar', 'baz']
        
        b = b'\x01'
        with mock.patch('peix.format.os', new=BytesMock(b + junk)):
            eff = EixFileFormat()
            assert eff.read_hashed_string(l) == 'bar'

    def test_read_hashed_word(self):

        # empty vector
        b = b'\x00'
        with mock.patch('peix.format.os', new=BytesMock(b + junk)):
            eff = EixFileFormat()
            assert eff.read_hashed_words(['foo', 'bar', 'baz']) == ''

        # single item
        b = b'\x01\x00'
        with mock.patch('peix.format.os', new=BytesMock(b + junk)):
            eff = EixFileFormat()
            assert eff.read_hashed_words(['foo', 'bar', 'baz']) == 'foo'

        # multiple items - should be concatenated with a whitespace
        b = b'\x02\x00\x01'
        with mock.patch('peix.format.os', new=BytesMock(b + junk)):
            eff = EixFileFormat()
            assert eff.read_hashed_words(['foo', 'bar', 'baz']) == 'foo bar'

    def test_read_magic(self):

        b = b'eix\n'
        with mock.patch('peix.format.os', new=BytesMock(b + junk)):
            EixFileFormat().read_magic()

        b = b'foobar'
        with mock.patch('peix.format.os', new=BytesMock(b + junk)):
            with pytest.raises(AssertionError):
                EixFileFormat().read_magic()
