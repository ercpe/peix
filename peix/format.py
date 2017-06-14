# -*- coding: utf-8 -*-
import os


class EixFileFormat(object):

    def __init__(self):
        self.fd = None
        
        self.file_format_version = None

    def read_magic(self):
        magic_bytes = os.read(self.fd, 4)
        assert magic_bytes == b'eix\n'

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

        bytes_to_read = 0
        number_bytes = b''

        last_byte = None
        while True:
            current_byte = os.read(self.fd, 1)
            if current_byte == b'\xff':
                bytes_to_read += 1
            elif current_byte == b'\x00' and last_byte == b'\xff':
                number_bytes += b'\xff'
                bytes_to_read -= 2
                break
            else:
                os.lseek(self.fd, -1, os.SEEK_CUR)
                break

            last_byte = current_byte

        number_bytes += os.read(self.fd, bytes_to_read +1)
        return int.from_bytes(number_bytes, byteorder='big')

    def read_vector(self, element_func):
        # Vectors (or lists) are extensively used throughout the index file. They are stored as the number of elements,
        # followed by the elements themselves.
        
        return [element_func() for _ in range(0, self.read_number())]

    def read_string(self):
        # Strings are stored as a vector of characters.
        buf = os.read(self.fd, self.read_number())
        return buf.decode('utf-8')

    def read_hash(self):
        # A hash is a vector of strings.
        return self.read_vector(self.read_string)

    def read_hashed_string(self, hash):
        # A number which is considered as an index in the corresponding hash; 0 denotes the first string of the hash,
        # 1 the second, ...
        return hash[self.read_number()]

    def read_hashed_words(self, hash):
        # A vector of HashedStrings. The resulting strings are meant to be concatenated, with spaces as separators.
        return ' '.join(self.read_vector(lambda: hash[self.read_number()]))
