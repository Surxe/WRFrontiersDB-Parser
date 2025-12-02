
import sys

from pathlib import Path
import argparse
from argparse import Namespace
from typing import Optional
from optionsconfig import init_options, ArgumentWriter
from options import set_options
from parse.parse import main as parse_main
from push.push import main as push_main
from parse.process_parsed_images import main as process_images_main

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_log_file_path(args: Namespace) -> Optional[str]:
    """
    Determine the log file path from the provided arguments.
    
    Args:
        args (Namespace): Parsed command line arguments
    Returns:
        Path: Log file path
    """
    if hasattr(args, 'export_dir') and args.export_dir:
        # path/to/exportdir/2025-09-30
        # output to cwd/logs/2025-09-30.log
        export_dir = Path(args.export_dir)
        version_date = export_dir.name
        log_dir = Path('logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{version_date}.log"
        return Path(log_file)
    return Path('logs/default.log')

def main():
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

    log_file_path = get_log_file_path(args)

    options = init_options(args, log_file=log_file_path)
    set_options(options)

    from optionsconfig import logger

    if options.should_parse:
        logger.debug(f"should_parse is set to {options.should_parse}, proceeding with parsing.")
        parse_main()

    process_images_main()

    if options.should_push_data:
        logger.debug(f"should_push_data is set to {options.should_push_data}, proceeding with pushing data.")
        push_main()

if __name__ == "__main__":
    main()