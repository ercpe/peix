# -*- coding: utf-8 -*-
import os


class EixFileFormat(object):

    def __init__(self):
        self.fd = None
        
        self.file_format_version = None
        self.no_categories = None
        self.overlays = self.eapi = self.licenses = self.keywords = self.use_flags = self.slots = self.world_sets = None
        self.dependencies_stored = False
        self.required_use_stored = False

    def read_magic(self):
        magic_bytes = os.read(self.fd, 4)
        assert magic_bytes == b'eix\n'

    def read_header(self):
        self.read_magic()
        self.file_format_version = self.read_number()
        self.no_categories = self.read_number()
        self.overlays = self.read_overlays()
        self.eapi = self.read_hash()
        self.licenses = self.read_hash()
        self.keywords = self.read_hash()
        self.use_flags = self.read_hash()
        self.slots = self.read_hash()
        self.world_sets = self.read_hash()

        flags = self.read_number()
        self.dependencies_stored = flags & 0x01 == 0x01
        self.required_use_stored = flags & 0x02 == 0x02

        depend_hash_length = self.read_number()
        self.depend = self.read_hash()

    def read_number(self):
        # From: https://github.com/vaeth/eix/blob/master/doc/eix-db.txt.in#number
        #
        # The index file contains non-negative integer values only. The format we use avoids fixed length integers by
        # encoding the number of bytes into the integer itself. It has a bias towards numbers smaller than 0xFF, which
        # are encoded into a single byte.
        #
        # To determine the number of bytes used, you must first count how often the byte 0xFF occurs at the beginning of
        # the number. Let n be this count (n may be 0). Then, as a rule, there will follow n+1 bytes that contain the
        # actual integer stored in big-endian byte order (highest byte first).
        #
        # But since it would be impossible to store any number that has a leading 0xFF with this format, a leading 0xFF
        # is stored as 0x00. Meaning, if a 0x00 byte follows the last 0xFF, you must interpret this byte as 0xFF inside
        # the number.
        #
        # Examples:
        #
        # Number	    Bytes stored in the file
        # 0x00	        0x00
        # 0xFE	        0xFE
        # 0xFF	        0xFF 0x00
        # 0x0100	    0xFF 0x01 0x00
        # 0x01FF	    0xFF 0x01 0xFF
        # 0xFEFF	    0xFF 0xFE 0xFF
        # 0xFF00	    0xFF 0xFF 0x00 0x00
        # 0xFF01	    0xFF 0xFF 0x00 0x01
        # 0x010000	    0xFF 0xFF 0x01 0x00 0x00
        # 0xABCDEF	    0xFF 0xFF 0xAB 0xCD 0xEF
        # 0xFFABCD	    0xFF 0xFF 0xFF 0x00 0xAB 0xCD
        # 0x01ABCDEF	0xFF 0xFF 0xFF 0x01 0xAB 0xCD 0xEF

        num_0xff = 1
        number_bytes = b''

        while True:
            current_byte = os.read(self.fd, 1)

            if current_byte == b'\xFF':
                num_0xff += 1
            elif current_byte == b'\x00' and num_0xff > 1:
                number_bytes += b'\xff'
                break
            else:
                os.lseek(self.fd, -1, os.SEEK_CUR)
                break

        number_bytes += os.read(self.fd, num_0xff)
        return int.from_bytes(number_bytes, byteorder='big')

    def read_vector(self, element_func):
        num_elements = self.read_number()
        l = []
        for _ in range(0, num_elements):
            o = element_func()
            print("Current element: %s" % (o, ))
            l.append(o)
        return l

    def read_string(self):
        buf = os.read(self.fd, self.read_number())
        print("buf: %s" % (buf, ))
        return buf.decode('utf-8')

    def read_overlays(self):
        return self.read_vector(self.read_overlay)

    def read_overlay(self):
        return self.read_string(), self.read_string()

    def read_hash(self):
        return self.read_vector(self.read_string)
