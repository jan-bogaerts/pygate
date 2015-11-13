
from ConfigParser import *

modules = []                                    #all the mmodule names that should be loaded



def load():
    """Load config data"""
    global modules
    c = ConfigParser()
    if c.read('../config/pygate.config'):
        modules = c.get('general', 'modules')