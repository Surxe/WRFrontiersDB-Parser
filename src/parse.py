from dotenv import load_dotenv
load_dotenv()

from utils import clear_dir

# call other parsers
from parsers.module import *
from parsers.localization import *

clear_dir("output")  # Clear the data directory before parsing

parse_localization()
print()
parse_modules()