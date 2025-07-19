from dotenv import load_dotenv
# Force reload .env file, overriding any existing environment variables
load_dotenv(override=True)

from utils import clear_dir

# call other parsers
from parsers.module import *
from parsers.localization import *

clear_dir("output")  # Clear the data directory before parsing

parse_localization()
print()
parse_modules() #module relies on english localization being added to each key just as a helpful Ctrl+F reference