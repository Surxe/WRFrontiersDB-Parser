from dotenv import load_dotenv
# Force reload .env file, overriding any existing environment variables
load_dotenv(override=True)

from utils import clear_dir

# call other parsers
from parsers.module import *
from parsers.localization import *
from parsers.pilot import *
from parsers.progression_table import *

clear_dir("output")  # Clear the data directory before parsing

parse_localizations()
print()
#parse_modules() #module relies on english localization being added to each key just as a helpful Ctrl+F reference
#parse_pilots()  # Pilot parser relies on module data being parsed first
parse_progression_table()