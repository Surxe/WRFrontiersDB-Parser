from typing import Literal

"""
# Schema
* **env** - Environment variable name (UPPER_CASE)
* **arg** - Command line argument (kebab-case with --)
* **type** - Python type (bool, str, Path, Literal)
* **default** - Default value. None means its required if any depends_on option is True
* **help** - Description text
* **section** - Logical grouping name
* **depends_on** - Optional. List of option names this option depends on (required when ANY of those options is True)
* **sensitive** - Boolean flag for password masking

# Patterns
* **should_** - Main action flags (e.g., `should_parse`)
"""

OPTIONS_SCHEMA = {
    "SHOULD_PARSE": {
        "env": "SHOULD_PARSE",
        "arg": "--should-parse",
        "type": bool,
        "default": False,
        "section": "Parse",
        "help": "Whether to parse the game files after downloading."
    },
    "GAME_NAME": {
        "env": "GAME_NAME",
        "arg": "--game-name",
        "type": str,
        "default": "WRFrontiers",
        "section": "Parse",
        "depends_on": ["SHOULD_PARSE"],
        "help": "Name of the game to download."
    },
    "EXPORT_DIR": {
        "env": "EXPORT_DIR",
        "arg": "--export-dir",
        "type": str,
        "default": None,
        "section": "Parse",
        "depends_on": ["SHOULD_PARSE"],
        "help": "Directory where the exported game JSON files are stored."
    },
    "SHOULD_PUSH_DATA": {
        "env": "SHOULD_PUSH_DATA",
        "arg": "--should-push-data",
        "type": bool,
        "default": False,
        "section": "Push Data",
        "help": "Whether to push parsed data to the data repository."
    },
    "GAME_VERSION": {
        "env": "GAME_VERSION",
        "arg": "--game-version",
        "type": str,
        "default": None,
        "section": "Push Data",
        "depends_on": ["SHOULD_PUSH_DATA"],
        "help": "Version of the game being processed, as its release date yyyy-mm-dd."
    },
    "CURRENT_IS_LATEST": {
        "env": "CURRENT_IS_LATEST",
        "arg": "--current-is-latest",
        "type": bool,
        "default": True,
        "section": "Push Data",
        "depends_on": ["SHOULD_PUSH_DATA"],
        "help": "Whether to also push data to the 'current' directory (in addition to archive)."
    },
    "TARGET_BRANCH": {
        "env": "TARGET_BRANCH",
        "arg": "--target-branch",
        "type": str,
        "default": "testing-grounds",
        "section": "Push Data",
        "depends_on": ["SHOULD_PUSH_DATA"],
        "help": "Target branch to push data to in the data repository."
    },
    "GH_DATA_REPO_PAT": {
        "env": "GH_DATA_REPO_PAT",
        "arg": "--gh-data-repo-pat",
        "type": str,
        "default": None,
        "section": "Push Data",
        "depends_on": ["SHOULD_PUSH_DATA"],
        "sensitive": True,
        "help": "PAT token to the GitHub repository that stores the data."
    },
    "LOG_LEVEL": {
        "env": "LOG_LEVEL",
        "arg": "--log-level",
        "type": Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "default": "DEBUG",
        "section": "Both",
        "help": "Logging level. Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL."
    },
    "OUTPUT_DIR": {
        "env": "OUTPUT_DIR",
        "arg": "--output-dir",
        "type": str,
        "default": None,
        "section": "Both",
        "depends_on": ["SHOULD_PARSE", "SHOULD_PUSH_DATA"],
        "help": "Directory where the parser will output files."
    },
}