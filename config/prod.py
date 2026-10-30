import os

from .base import *


DEBUG = False
TESTING = False
SECRET_KEY = os.environ["SECRET_KEY"]