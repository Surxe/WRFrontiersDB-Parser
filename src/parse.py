from dotenv import load_dotenv
load_dotenv()
import os

EXPORTS_PATH = os.getenv("EXPORTS_PATH", "error")
print(f"EXPORTS_PATH: {EXPORTS_PATH}")

from utils import clear_dir

# call other parsers
from parsers.module import *

clear_dir("data")  # Clear the data directory before parsing

parse_modules()