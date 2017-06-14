# -*- coding: utf-8 -*-
import os
import collections
from peix.format import EixFileFormat


class Package(collections.namedtuple('Package', ['category', 'name', 'description', 'homepage', 'license', 'versions'])):
    def __str__(self):
        return "%s/%s" % (self.category, self.name)


class Version(collections.namedtuple('Version', [
    'eapi', 'arch_mask', 'properties_mask', 'restrict_mask', 'keywords', 'version_parts', 'slot', 'overlay', 'uses',
    'depend', 'rdepend', 'pdepend', 'hdepend'
])):
    VTYPE_GARBAGE = 0  # garbage that was found after any valid version string
    VTYPE_ALPHA = 1  # number of "_alpha" (may be empty)
    VTYPE_BETA = 2  # number of "_beta" (may be empty)
    VTYPE_PRE = 3  # number of "_pre" (may be empty)
    VTYPE_RC = 4  # number of "_rc" (may be empty)
    VTYPE_REV = 5  # number of "-r" (may be empty)
    VTYPE_INTER_REV = 6  # number of inter-revision [2]
    VTYPE_PATCH = 7  # number of "_p" (may be empty)
    VTYPE_CHAR = 8  # single character
    VTYPE_PRIMARY = 9  # numeric version part
    VTYPE_FIRST = 10  # first numeric version part

    def __init__(self, *args, **kwargs):
        super(Version, self).__init__()
        self.version_str = None

    def __str__(self):
        if self.version_str is None:
            # Prefix	Name
            # "." (dot)	primary, inter_rev
            # "" (empty)	first, char, garbage
            # "_alpha"	alpha
            # "_beta"	beta
            # "_pre"	pre
            # "_rc"	rc
            # "-r"	revision
            # "_p"	patch
            prefixes = {
                Version.VTYPE_PRIMARY: '.',
                Version.VTYPE_INTER_REV: '.',
                Version.VTYPE_FIRST: '',
                Version.VTYPE_CHAR: '',
                Version.VTYPE_GARBAGE: '',
                Version.VTYPE_ALPHA: '_alpha',
                Version.VTYPE_BETA: '_beta',
                Version.VTYPE_PRE: '_pre',
                Version.VTYPE_RC: '_rc',
                Version.VTYPE_REV: '_pre',
                Version.VTYPE_PATCH: '_p',
            }
            self.version_str = ''.join(["%s%s" % (prefixes[vtype], vstr) for vtype, vstr in self.version_parts])

        return self.version_str

    @property
    def masked_package_mask(self):
        return self.arch_mask & 0x01 == 0x01

    @property
    def masked_by_profile(self):
        return self.arch_mask & 0x02 == 0x02

    @property
    def in_system(self):
        return self.arch_mask & 0x04 == 0x04

    @property
    def in_world(self):
        return self.arch_mask & 0x08 == 0x08

    @property
    def in_world_sets(self):
        return self.arch_mask & 0x10 == 0x10

    @property
    def in_profile(self):
        return self.arch_mask & 0x20 == 0x20

    restrict_binchecks = property(lambda self: self.restrict_mask & 0x0001 == 0x0001)
    restrict_strip = property(lambda self: self.restrict_mask & 0x0002 == 0x0002)
    restrict_test = property(lambda self: self.restrict_mask & 0x0004 == 0x0004)
    restrict_userpriv = property(lambda self: self.restrict_mask & 0x0008 == 0x0008)
    restrict_installsources = property(lambda self: self.restrict_mask & 0x0010 == 0x0010)
    restrict_fetch = property(lambda self: self.restrict_mask & 0x0020 == 0x0020)
    restrict_mirror = property(lambda self: self.restrict_mask & 0x0040 == 0x0040)
    restrict_primaryuri = property(lambda self: self.restrict_mask & 0x0080 == 0x0080)
    restrict_bindist = property(lambda self: self.restrict_mask & 0x0100 == 0x0100)
    restrict_parallel = property(lambda self: self.restrict_mask & 0x0200 == 0x0200)


class EixDB(EixFileFormat):
    
    def __init__(self, cache_file):
        super(EixDB, self).__init__()
        self.dependencies_stored = False
        self.required_use_stored = False
        self.depend = None
        self.no_categories = None
        self.overlays = self.eapi = self.licenses = self.keywords = self.use_flags = self.slots = self.world_sets \
            = self.packages = None
        self.cache_file = cache_file
    
    def read(self):
        try:
            self.fd = os.open(self.cache_file, os.O_RDONLY)
            
            self.read_database()
            
        finally:
            if self.fd:
                os.close(self.fd)

    def read_database(self):
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


    def read_overlay(self):
        return self.read_string(), self.read_string()

    def read_overlays(self):
        return self.read_vector(self.read_overlay)

    def read_packages(self):

        def _inner():
            for _ in range(0, self.no_categories):
                category = self.read_string()
                for p in self.read_vector(lambda: self.read_package(category)):
                    yield p

        return list(_inner())

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

    def read_package(self, category_name):
        offset_to_next = self.read_number()

        name = self.read_string()
        desc = self.read_string()
        homepage = self.read_string()
        license = self.licenses[self.read_number()]
        versions = self.read_vector(self.read_version)
        return Package(category_name, name, desc, homepage, license, versions)

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
