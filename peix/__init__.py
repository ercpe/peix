# -*- coding: utf-8 -*-
import os

from peix.format import EixFileFormat


class EixDB(EixFileFormat):
    
    def __init__(self, cache_file):
        super(EixDB, self).__init__()
        self.cache_file = cache_file
    
    def read(self):
        try:
            self.fd = os.open(self.cache_file, os.O_RDONLY)
            
            self.read_header()
            
        finally:
            if self.fd:
                os.close(self.fd)
