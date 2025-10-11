
import sys
import os
# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import argparse
from options import init_options, ArgumentWriter
from parse.parse import main as parse_main
#from push.push import main as push_main

# Parse command-line arguments for Params fields
parser = argparse.ArgumentParser(
        description="WRFrontiers-Parser - Complete game asset parser pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
For detailed documentation including all command line arguments, configuration options,
and troubleshooting information, please see the README.md file.

Quick Examples:
  python run.py
        """
    )
argument_writer = ArgumentWriter()
argument_writer.add_arguments(parser)
args = parser.parse_args()

OPTIONS = init_options(args)

if OPTIONS.should_parse:
    parse_main()
if OPTIONS.should_push_data:
    pass
    #push_main()