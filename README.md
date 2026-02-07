# WRFrontiersDB-Parser
War Robots Frontiers Database Parser

## Options

### Command Line Argument Usage

For each option, the command line argument may be used at runtime instead of providing it in the `.env`.

```bash
python src/run.py                    # Run all steps with default/env values
python src/run.py --log-level INFO   # Run all steps with default/env values, except with LOG_LEVEL INFO
```

### Parameters

<!-- BEGIN_GENERATED_OPTIONS -->
#### Parse

* **SHOULD_PARSE** - Whether to parse the game files after downloading.
  - Default: `"false"`
  - Command line: `--should-parse`

* **GAME_NAME** - Name of the game to download.
  - Default: `"WRFrontiers"`
  - Command line: `--game-name`
  - Depends on: `SHOULD_PARSE`

* **EXPORT_DIR** - Directory where the exported game JSON files are stored.
  - Example: `"C:/WRFrontiersDB/ExportData"`
  - Default: None - required when SHOULD_PARSE is True
  - Command line: `--export-dir`
  - Depends on: `SHOULD_PARSE`


#### Push Data

* **SHOULD_PUSH_DATA** - Whether to push parsed data to the data repository.
  - Default: `"false"`
  - Command line: `--should-push-data`

* **GAME_VERSION** - Version of the game being processed, as its release date yyyy-mm-dd.
  - Example: `"2025-10-28"`
  - Default: None - required when SHOULD_PUSH_DATA is True
  - Command line: `--game-version`
  - Depends on: `SHOULD_PUSH_DATA`

* **PUSH_TO_ARCHIVE** - Whether to push data to the 'archive' directory.
  - Default: `"true"`
  - Command line: `--push-to-archive`
  - Depends on: `SHOULD_PUSH_DATA`

* **PUSH_TO_CURRENT** - Whether to push data to the 'current' directory.
  - Default: `"true"`
  - Command line: `--push-to-current`
  - Depends on: `SHOULD_PUSH_DATA`

* **TARGET_BRANCH** - Target branch to push data to in the data repository.
  - Default: `"testing-grounds"`
  - Command line: `--target-branch`
  - Depends on: `SHOULD_PUSH_DATA`

* **SHOULD_RECLONE** - Whether to reclone the data repository from scratch before pushing data. If false, will assume the repository is already cloned at GH_DATA_REPO_DIR and is current.
  - Default: `"true"`
  - Command line: `--should-reclone`
  - Depends on: `SHOULD_PUSH_DATA`
  - Recommended to be True unless running in bulk.

* **GH_DATA_REPO_PAT** - PAT token to the GitHub repository that stores the data.
  - Example: `"github_pat_XXXXXXXXXXXXXXXX"`
  - Default: None - required when SHOULD_PUSH_DATA is True
  - Command line: `--gh-data-repo-pat`
  - Depends on: `SHOULD_PUSH_DATA`

* **TRIGGER_DATA_WORKFLOW** - Whether to trigger the data repository workflow after pushing data to it. Requires PUSH_TO_ARCHIVE to be true.
  - Default: `"false"`
  - Command line: `--trigger-data-workflow`
  - Depends on: `SHOULD_PUSH_DATA`

* **SHOULD_PUSH_TEXTURES** - Whether to push extracted textures to the data repository.
  - Default: `"false"`
  - Command line: `--should-push-textures`
  - Depends on: `SHOULD_PUSH_DATA`


#### Store Data

* **GH_DATA_REPO_DIR** - Directory of the GitHub repository that stores the data, relative to the current working directory.
  - Example: `"C:/WRFrontiersDB/Data"`
  - Default: `"WRFrontiersDB-Data"`
  - Command line: `--gh-data-repo-dir`
  - Depends on: `SHOULD_PUSH_DATA`


#### Both

* **LOG_LEVEL** - Logging level. Must be one of: TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL.
  - Default: `"DEBUG"`
  - Command line: `--log-level`

* **OUTPUT_DIR** - Directory where the parser will output files and where data is pushed from.
  - Example: `"C:/WRFrontiersDB/Output"`
  - Default: None - required when SHOULD_PARSE or SHOULD_PUSH_DATA is True
  - Command line: `--output-dir`
  - Depends on: `SHOULD_PARSE`, `SHOULD_PUSH_DATA`

* **TEXTURE_OUTPUT_DIR** - Directory where extracted textures will be saved. Unlike OUTPUT_DIR, this will not be cleared on each run.
  - Example: `"C:/WRFrontiersDB/Textures"`
  - Default: None - required when SHOULD_PARSE or SHOULD_PUSH_DATA is True
  - Command line: `--texture-output-dir`
  - Depends on: `SHOULD_PARSE`, `SHOULD_PUSH_DATA`


<!-- END_GENERATED_OPTIONS -->
### Miscellaneous Option Behavior

* An option's value is determined by the following priority, in descending order
  * Argument
  * Option
  * Default
* If all options prefixed with `SHOULD_` are defaulted to `False`, they are instead all defaulted to `True` for ease of use
* Options are only required if their section's `SHOULD_` option is `True`