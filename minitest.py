
from snoop import pp
from pathlib import Path

import sys

import snoop

import minilib

minilib.x += 1

print(minilib.x)

m = sys.modules['minilib']
