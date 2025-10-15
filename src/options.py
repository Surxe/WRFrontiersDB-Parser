from dotenv import load_dotenv

import os
import sys
import os
from typing import Literal, get_origin, get_args
from pathlib import Path
from loguru import logger
load_dotenv()

"""
Central configuration schema to provide a single source of truth for all documentation and functionality of options/args
"""

from options_schema import OPTIONS_SCHEMA
from argparse import ArgumentParser, Namespace

class ArgumentWriter:
    """
    Helper class to write command line arguments based on OPTIONS_SCHEMA
    """

    def __init__(self):
        self.schema = OPTIONS_SCHEMA

    def add_arguments(self, parser: ArgumentParser):
        for option_name, details in self.schema.items():
            arg_name = details["arg"]
            arg_type = details["type"]
            default = details["default"]
            help_text = details.get("help", "") + f" (default: {default})"
            
            if arg_type == bool:
                parser.add_argument(arg_name, action='store_true', default=None, help=help_text)
                logger.debug(f"Added boolean argument {arg_name} with action 'store_true'")
            elif get_origin(arg_type) is Literal:
                # Handle Literal types by extracting the choices
                choices = list(get_args(arg_type))
                parser.add_argument(arg_name, choices=choices, default=None, help=help_text)
                logger.debug(f"Added choice argument {arg_name} with choices {choices} and default {default}")
            elif arg_type == Path:
                # Handle Path types
                parser.add_argument(arg_name, type=str, default=None, help=help_text)
                logger.debug(f"Added path argument {arg_name} with default {default}")
            else:
                parser.add_argument(arg_name, type=arg_type, default=None, help=help_text)
                logger.debug(f"Added argument {arg_name} with type {arg_type} and default {default}")

class Options:
    """
    A class to hold options for the application.
    """
    def __init__(self, args: Namespace | None = None):

        # Initialize all options in the following preference
        # 1. Direct args (if provided)
        # 2. Environment variables (if set)
        # 3. Defaults from OPTIONS_SCHEMA

        # If args is provided, it should be a Namespace from argparse
        if args is not None:
            args_dict = vars(args)
        else:
            args_dict = {}

        # Identify root options (options that other options depend on)
        self.root_options = []
        for option_name, details in OPTIONS_SCHEMA.items():
            # An option is a root option if other options depend on it
            is_root = any(
                option_name in OPTIONS_SCHEMA[other_option].get("depends_on", [])
                for other_option in OPTIONS_SCHEMA
            )
            if is_root:
                self.root_options.append(option_name)

        # Process the schema to set all attributes
        options = self._process_schema(OPTIONS_SCHEMA, args_dict)

        # Set attributes dynamically using lowercase underscore format
        for key, value in options.items():
            # Convert schema key (UPPER_CASE) to attribute name (lower_case)
            attr_name = key.lower()
            setattr(self, attr_name, value)
            logger.debug(f"Set attribute {attr_name} to value: {value if not details.get('sensitive', False) else '***HIDDEN***'}")

        self.validate()

        # Setup loguru logging to /logs dir
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        if hasattr(self, 'output_dir') and self.output_dir:
            log_filename = str(self.output_dir).replace('\\', '/').rstrip('/').split('/')[-1] + '.log'
            # i.e. F:/WRF/2025-08-12/<exports> to 2025-08-12.log
        else:
            log_filename = 'default.log'
        log_path = os.path.join(logs_dir, log_filename)
        logger.remove()
        
        # Clear the log file before adding the handler
        with open(log_path, 'w') as f:
            pass
        logger.add(log_path, level=self.log_level, rotation="10 MB", retention="10 days", enqueue=True)
        logger.add(sys.stdout, level=self.log_level)
        
        self.log()

    def _process_schema(self, schema: dict, args_dict: dict) -> dict:
        """Process the option schema, env options, and args to get the combined options."""

        options = {}

        # Process all options in the schema
        for option_name, details in schema.items():
            # Convert arg name to attribute name (remove -- and convert - to _)
            attr_name = details["arg"].lstrip('--').replace('-', '_')
            
            # Get value in order of priority: args -> env -> default
            value = None

            logger.debug(f"Processing option: {option_name} (attr: {attr_name})")

            # 1. Check args first
            if attr_name in args_dict and args_dict[attr_name] is not None:
                value = args_dict[attr_name]
                logger.debug(f"Argument {attr_name} found in args with value: {value if not details.get('sensitive', False) else '***HIDDEN***'}")
            # 2. Check environment variable
            elif details["env"] in os.environ:
                env_value = os.environ[details["env"]]
                logger.debug(f"Environment variable {details['env']} found with value: {env_value if not details.get('sensitive', False) else '***HIDDEN***'}")
                # Convert environment string to proper type
                if details["type"] == bool:
                    value = is_truthy(env_value)
                elif details["type"] == Path:
                    value = Path(env_value) if env_value else None
                elif get_origin(details["type"]) is Literal:
                    # For Literal types, use the string value directly if it's valid
                    valid_choices = get_args(details["type"])
                    value = env_value if env_value in valid_choices else details["default"]
                else:
                    value = details["type"](env_value) if env_value else details["default"]
            # 3. Use default
            else:
                value = details["default"]
            
            # Store
            options[option_name] = value

        # If none of the root options have been explicitly set (from args or env), default all to true for ease of use
        # Check if any root option was explicitly provided (not just defaulted from schema)
        explicitly_set_root_options = []
        for root_option in self.root_options:
            attr_name = OPTIONS_SCHEMA[root_option]["arg"].lstrip('--').replace('-', '_')
            # Check if it was in args or environment
            if (attr_name in args_dict and args_dict[attr_name] is not None) or \
               OPTIONS_SCHEMA[root_option]["env"] in os.environ:
                explicitly_set_root_options.append(root_option)
        
        if not explicitly_set_root_options:
            # No root options were explicitly set, default all to True
            for root_option in self.root_options:
                options[root_option] = True
            logger.debug("No root options explicitly set, defaulting all to True")

        return options
    
    def validate(self) -> None:
        # Validate that options with dependencies have their requirements met
        options_as_dict = {k.upper(): v for k, v in self.__dict__.items() if k != 'root_options'}
        
        # Check each option that has dependencies
        for option_name, details in OPTIONS_SCHEMA.items():
            depends_on_list = details.get("depends_on", [])
            if not depends_on_list:
                continue
            
            # Check if ANY of the dependencies are True
            any_dependency_true = any(
                options_as_dict.get(dep_option) is True
                for dep_option in depends_on_list
            )
            
            if any_dependency_true:
                value = options_as_dict.get(option_name)
                if value is None:
                    # Build a helpful error message
                    active_dependencies = [
                        dep for dep in depends_on_list
                        if options_as_dict.get(dep) is True
                    ]
                    raise ValueError(
                        f"{option_name} is required when any of the following are true: "
                        f"{', '.join(depends_on_list)}. Currently active: {', '.join(active_dependencies)}"
                    )
                logger.debug(f"Dependent option {option_name} is set to {value if not details.get('sensitive', False) else '***HIDDEN***'}")
        
    def log(self):
        """
        Logs the options.
        """
        # Dynamically log all attributes that were set from the schema
        log_lines = ["Options initialized with:"]
        
        for option_name, details in OPTIONS_SCHEMA.items():
            attr_name = details["arg"].lstrip('--').replace('-', '_')
            if hasattr(self, attr_name):
                value = getattr(self, attr_name)
                # Don't log sensitive information
                if details.get("sensitive", False):
                    value = "***HIDDEN***"
                log_lines.append(f"{option_name}: {value}")
        
        logger.info("\n".join(log_lines))
    
# Helper to initialize OPTIONS with direct args if available
def init_options(args: Namespace | None = None):
    global OPTIONS
    OPTIONS = Options(args)
    return OPTIONS

def is_truthy(string):
    TRUE_THO = [
        True,
        'true',
        'True',
        'TRUE',
        't',
        'T',
        1,
    ]
    return string in TRUE_THO