# Patch the xcal parser into vivisect.parsers.

from . import xcal

import vivisect.parsers
vivisect.parsers.xcal = xcal

import sys
sys.modules['vivisect.parsers.xcal'] = xcal
