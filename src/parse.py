from dotenv import load_dotenv
load_dotenv()
import os

EXPORTS_PATH = os.getenv("EXPORTS_PATH", "error")
print(f"EXPORTS_PATH: {EXPORTS_PATH}")

# call other parsers
from parsers.module import parse_modules

parse_modules()