from typing import Literal

"""
# Schema
* **env** - Environment variable name (UPPER_CASE)
* **arg** - Command line argument (kebab-case with --)
* **type** - Python type (bool, str, Path, Literal)
* **default** - Default value. None means its required if it's root option is True
* **help** - Description text
* **section** - Logical grouping name
* **section_options** - Nested sub-options
* **sensitive** - Boolean flag for password masking

# Patterns
* **should_** - Main action flags (e.g., `should_download_steam_game`)
"""

OPTIONS_SCHEMA = {
    "LOG_LEVEL": {
        "env": "LOG_LEVEL",
        "arg": "--log-level",
        "type": Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "default": "DEBUG",
        "section": "Logging",
        "help": "Logging level. Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL."
    },
    "SHOULD_PARSE": {
        "env": "SHOULD_PARSE",
        "arg": "--should-parse",
        "type": bool,
        "default": False,
        "help": "Whether to parse the game files after downloading.",
        "section": "Parse",
        "section_options": {
            "GAME_NAME": {
                "env": "GAME_NAME",
                "arg": "--game-name",
                "type": str,
                "default": "WRFrontiers",
                "help": "Name of the game to download.",
                "section": "Parse",
            },
            "EXPORT_DIR": {
                "env": "EXPORT_DIR",
                "arg": "--export-dir",
                "type": str,
                "default": None,
                "help": "Directory where the exported game JSON files are stored.",
                "section": "Parse",
            },
            "OUTPUT_DIR": {
                "env": "OUTPUT_DIR",
                "arg": "--output-dir",
                "type": str,
                "default": None,
                "help": "Directory where the parser will output files.",
                "section": "Parse",
            },
        }
    },
    "SHOULD_PUSH_DATA": {
        "env": "SHOULD_PUSH_DATA",
        "arg": "--should-push-data",
        "type": bool,
        "default": False,
        "help": "Whether to push parsed data to the data repository.",
        "section": "Push Data",
        "section_options": {
            "GAME_VERSION": {
                "env": "GAME_VERSION",
                "arg": "--game-version",
                "type": str,
                "default": None,
                "help": "Version of the game being processed, as its release date yyyy-mm-dd.",
            },
            "GH_DATA_REPO_PAT": {
                "env": "GH_DATA_REPO_PAT",
                "arg": "--gh-data-repo-pat",
                "type": str,
                "default": None,
                "help": "PAT token to the GitHub repository that stores the data.",
                "sensitive": True,
            },
        }
    },
}