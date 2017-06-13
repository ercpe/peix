# -*- coding: utf-8 -*-
import os
import collections

class Package(collections.namedtuple('Package', ('name', 'description', 'homepage', 'licenses'))):
    versions = None


class EixFileFormat(object):

    def __init__(self):
        self.fd = None
        
        self.file_format_version = None
        self.no_categories = None
        self.overlays = self.eapi = self.licenses = self.keywords = self.use_flags = self.slots = self.world_sets \
            = self.categories = None
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
        # fixme
        #self.depend = self.read_hash()
        os.lseek(self.fd, depend_hash_length, os.SEEK_CUR)

        self.categories = self.read_categories_and_packages()

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
        return [element_func() for _ in range(0, self.read_number())]

    def read_string(self):
        buf = os.read(self.fd, self.read_number())
        return buf.decode('utf-8')

    def read_overlays(self):
        return self.read_vector(self.read_overlay)

    def read_overlay(self):
        return self.read_string(), self.read_string()

    def read_hash(self):
        return self.read_vector(self.read_string)

    def read_categories_and_packages(self):
        
        for _ in range(0, self.no_categories):
            category = self.read_string()
            print("%s:" % category)
            for p in self.read_vector(self.read_package):
                print("- %s", p)

    def read_package(self):
        offset_to_next = self.read_number()
        my_pos = os.lseek(self.fd, 0, os.SEEK_CUR)

        name = self.read_string()
        desc = self.read_string()
        homepage = self.read_string()
        license = self.licenses[self.read_number()]
        print("%s, %s, %s, %s" % (name, desc, homepage, license))
        versions = self.read_vector(self.read_version)
        print("versions: %s" % (versions))
        print("--")
        
        print("Current position: %s. Should be: %s" % (os.lseek(self.fd, 0, os.SEEK_CUR), my_pos+offset_to_next))
        assert os.lseek(self.fd, 0, os.SEEK_CUR) == my_pos+offset_to_next
        #os.lseek(self.fd, my_pos + offset_to_next, os.SEEK_SET)
        #return Package(self.read_string(), self.read_string(), self.read_string(), self.read_hashed_string(self.licenses))
    
    def read_hashed_string(self, hash):
        return hash[self.read_number()]

    def read_hashed_words(self, hash):
        return self.read_vector(lambda: hash[self.read_number()])

    def read_version(self):
        eapi = self.eapi[self.read_number()]
        print("EAPI: %s" % eapi)
        mask_bitmask = self.read_number()
        print("Mask: %s" % mask_bitmask)
        prop_bitmask = self.read_number()
        print("Prop Mask: %s" % prop_bitmask)
        restrict_bitmask = self.read_number()
        print("restr Mask: %s" % restrict_bitmask)
        keywords = self.read_hashed_words(self.keywords)
        print("Keywords: %s" % keywords)
        version_parts = self.read_vector(self.read_version_part)
        print("Version parts: %s" % version_parts)
        slot = self.read_hashed_string(self.slots)
        print("slot: %s" % slot)
        overlay_idx = self.read_number()
        print("overlay idx: %s (%s)" % (overlay_idx, self.overlays[overlay_idx]))
        use_flags = self.read_hashed_words(self.use_flags)
        print("uses: %s" % use_flags)
        required_use = self.read_hashed_words(self.use_flags)
        print("req use: %s" % required_use)
        #fixme
        if self.dependencies_stored:
            self.read_number()
            depend_idx = self.read_vector(self.read_number)
            rdepend_idx = self.read_vector(self.read_number)
            pdepend_idx = self.read_vector(self.read_number)
            hdepend_idx = self.read_vector(self.read_number)
            # depend_rdpepend_pdepend_hdepend_len = self.read_number()
            # os.lseek(self.fd, depend_rdpepend_pdepend_hdepend_len, os.SEEK_CUR)
        print("####")
        

    def read_version_part(self):
        # A VersionPart consists of two data: a number (referred to as type) and a "string" (referred to as value).
        # The number is encoded in the lower 5 bits of the length-part of the "string"; of course, the actual length is
        # shifted by the same number of bits.

        num = self.read_number()

        # * app-accessibility/SphinxTrain
        #     Available versions:  ~0.9.1-r1 1.0.8 {PYTHON_TARGETS="python2_7"}

        # 10 (first):  0
        # 9 (primary): 9
        # 8??:         1
        # 5 (rev)      -r1
        
        # remove the lower bits of `num` by shifting everything to the right
        str_len = num >> 5
        # extract the type (lower 5 bits) by masking out the `str_len` (the lower 5 bits)
        vp_type = num & ~(str_len << 5)

        buf = os.read(self.fd, str_len)
        return vp_type, buf.decode('utf-8')
