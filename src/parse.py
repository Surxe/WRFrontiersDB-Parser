from dotenv import load_dotenv
load_dotenv()

from utils import clear_dir

# call other parsers
from parsers.module import *

clear_dir("data")  # Clear the data directory before parsing

parse_modules()