import logging
from core.test.setup import setup_basic

logging.basicConfig(level=logging.WARN)

# WARNING: setup_basic() must be called before importing fixtures!
setup_basic()

from migration.test.fixtures import *
from core.test.fixtures import database, session