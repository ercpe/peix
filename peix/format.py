# -*- coding: utf-8 -*-
import os
import collections


class Package(collections.namedtuple('Package', ['category', 'name', 'description', 'homepage', 'license', 'versions'])):
    
    def __str__(self):
        return "%s/%s" % (self.category, self.name)


class Version(collections.namedtuple('Version', [
    'eapi', 'arch_mask', 'properties_mask', 'restrict_mask', 'keywords', 'version_parts', 'slot', 'overlay', 'uses',
    'depend', 'rdepend', 'pdepend', 'hdepend'
])):
    pass


class EixFileFormat(object):

    def __init__(self):
        self.fd = None
        
        self.file_format_version = None
        self.no_categories = None
        self.overlays = self.eapi = self.licenses = self.keywords = self.use_flags = self.slots = self.world_sets \
            = self.packages = None
        self.dependencies_stored = False
        self.required_use_stored = False
        self.depend = None

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

        self.packages = self.read_packages()

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

    def read_overlays(self):
        return self.read_vector(self.read_overlay)

    def read_overlay(self):
        return self.read_string(), self.read_string()

    def read_hash(self):
        # A hash is a vector of strings.
        return self.read_vector(self.read_string)

    def read_packages(self):
        
        def _inner():
            for _ in range(0, self.no_categories):
                category = self.read_string()
                for p in self.read_vector(lambda: self.read_package(category)):
                    yield p

        return list(_inner())

    def read_package(self, category_name):
        offset_to_next = self.read_number()

        name = self.read_string()
        desc = self.read_string()
        homepage = self.read_string()
        license = self.licenses[self.read_number()]
        versions = self.read_vector(self.read_version)
        return Package(category_name, name, desc, homepage, license, versions)
    
    def read_hashed_string(self, hash):
        # A number which is considered as an index in the corresponding hash; 0 denotes the first string of the hash,
        # 1 the second, ...
        return hash[self.read_number()]

    def read_hashed_words(self, hash):
        # A vector of HashedStrings. The resulting strings are meant to be concatenated, with spaces as separators.
        return ' '.join(self.read_vector(lambda: hash[self.read_number()]))

    def read_version(self):
        eapi = self.eapi[self.read_number()]
        mask_bitmask = self.read_number()
        prop_bitmask = self.read_number()
        restrict_bitmask = self.read_number()
        keywords = self.read_hashed_words(self.keywords)
        version_parts = self.read_vector(self.read_version_part)
        slot = self.read_hashed_string(self.slots)
        overlay_idx = self.read_number()
        use_flags = self.read_hashed_words(self.use_flags)
        required_use = self.read_hashed_words(self.use_flags)

        depend = None
        rdepend = None
        pdepend = None
        hdepend = None

        if self.dependencies_stored:
            self.read_number()
            depend = self.read_hashed_words(self.depend)
            rdepend = self.read_hashed_words(self.depend)
            pdepend = self.read_hashed_words(self.depend)
            hdepend = self.read_hashed_words(self.depend)

        return Version(eapi, mask_bitmask, prop_bitmask, restrict_bitmask, keywords, version_parts, slot or '0', self.overlays[overlay_idx],
                       use_flags, depend, rdepend, pdepend, hdepend)
        
    def read_version_part(self):
        # A VersionPart consists of two data: a number (referred to as type) and a "string" (referred to as value).
        # The number is encoded in the lower 5 bits of the length-part of the "string"; of course, the actual length is
        # shifted by the same number of bits.

        # A version string '0.9.1-r1' is split into the following parts:

        # 10 (first):  0
        # 9 (primary): 9
        # 9:           1
        # 5 (rev)      -r1

        num = self.read_number()

        # remove the lower bits of `num` by shifting everything to the right
        str_len = num >> 5
        # extract the type (lower 5 bits) by masking out the `str_len` (the lower 5 bits)
        vp_type = num & ~(str_len << 5)

        buf = os.read(self.fd, str_len)
        return vp_type, buf.decode('utf-8')
