# WRFrontiersDB-Parser
War Robots Frontiers Database Parser

## Setup

Create and activate a virtual environment for this repo, then install its dependencies:

```bash
# From the repo root (WRFrontiersDB-Parser/)
python -m venv .venv

# Activate it
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows (PowerShell/cmd)

# Install dependencies
pip install -r requirements.txt
```

Then copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

To leave the virtual environment, run `deactivate`.

## Patch-day development

A new game patch usually brings data the parser doesn't handle yet; the parse
still completes and publishes, logging each gap as a warning. Tooling for the fix:

* [`CLAUDE.md`](CLAUDE.md) - key-map conventions, parse-vs-skip rules, log levels.
* `tools/warning_report.py` - groups a parse log's thousands of lines into a short triage report, written to `reports/latest.md` (gitignored) for VS Code's markdown preview, and tracks a parse/skip/fix decision per group in `decisions/<version>.json` (gitignored, local only).
* `tools/patch_day.sh` - scratch parse + a git "review repo" of the parsed output, so each parser change shows up as a diff in VS Code.
* `tools/asset-viewer/serve.py` - click through the exported JSON (reads `EXPORT_DIR` from `.env`).
* `.claude/skills/patch-warnings` - the Claude Code skill that runs the process with two human approval gates.
* The end-to-end runbook is `PATCH_DAY.md` in WRFrontiersDB-Orchestrator.

## Maps

With `SHOULD_PARSE_MAPS`, the parse also cooks the 3D maps for the Site's `/maps` page from the
Exporter's map export (`MAPS_EXPORT_DIR`, BatchExport's map mode). Code: `src/parse/maps/`
(`cook.py` documents the output), `src/parse/parsers/map.py` (the map list).

| Output | Content |
|--------|---------|
| `Objects/Map.json` | The released maps (the game's queue list, `ST_MapNames`, the firing range) with their localized names, game modes and file names |
| `Maps/<Map>.glb` | Render geometry every match has, instanced and meshopt-compressed by gltfpack |
| `Maps/<Map>.foliage.glb` | Trees, bushes and grass, simplified hard; the Site toggles them |
| `Maps/<Map>.<Mode>.glb` | Geometry a game mode adds (e.g. Mont's drill), when there is any |
| `Maps/<Map>.json` | Per game mode, the pins: spawns, warp probes, beacons, power-up spawners, CTF objects |

The pinned gltfpack is downloaded into `build/gltfpack/` on first use. Cooking is deterministic,
and a map whose input did not change is copied from `build/map_cook_cache/`, so unchanged maps
stay byte-identical in the data repo. All 12 maps are ~85 MB.

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

* **SHOULD_PARSE_MAPS** - Whether to cook the 3D maps from the map export (MAPS_EXPORT_DIR) into Maps/ and list them in Objects/Map.json. Part of the parse, so only with SHOULD_PARSE.
  - Default: `"false"`
  - Command line: `--should-parse-maps`
  - Depends on: `SHOULD_PARSE`
  - Downloads the pinned gltfpack into build/gltfpack/ on first use. A map whose input is unchanged is copied from build/map_cook_cache/ instead of cooked again.

* **MAPS_EXPORT_DIR** - Directory of the Exporter's map export for this version (holds maps/<Map>/scene.json and assets/).
  - Example: `"C:/WRFrontiersDB/Maps/2025-10-28"`
  - Default: None - required when SHOULD_PARSE_MAPS is True
  - Command line: `--maps-export-dir`
  - Depends on: `SHOULD_PARSE_MAPS`


#### Push Data

* **SHOULD_PUSH_DATA** - Whether to push parsed data to the data repository.
  - Default: `"false"`
  - Command line: `--should-push-data`

* **GAME_VERSION** - Version of the game being processed, as its release date yyyy-mm-dd.
  - Example: `"2025-10-28"`
  - Default: None - required when SHOULD_PUSH_DATA is True
  - Command line: `--game-version`
  - Depends on: `SHOULD_PUSH_DATA`

* **SHOULD_PUSH_JSON** - Whether to push parsed JSON data to the data repository.
  - Default: `"true"`
  - Command line: `--should-push-json`
  - Depends on: `SHOULD_PUSH_DATA`

* **TARGET_BRANCH** - Target branch to push data to in the data repository.
  - Default: `"testing-grounds"`
  - Command line: `--target-branch`
  - Depends on: `SHOULD_PUSH_DATA`

* **SHOULD_RECLONE** - Whether to reclone the data repository from scratch before pushing data. If false, will assume the repository is already cloned at GH_DATA_REPO_DIR and is currently checked out.
  - Default: `"true"`
  - Command line: `--should-reclone`
  - Depends on: `SHOULD_PUSH_DATA`
  - Recommended to be True unless running in bulk.

* **ALLOW_DIRTY_PUSH** - Whether to push data even if the parser's working tree has uncommitted changes. If false, the push is refused, since the data commit is labelled with the parser's HEAD commit and would not match the code that produced it.
  - Default: `"false"`
  - Command line: `--allow-dirty-push`
  - Depends on: `SHOULD_PUSH_DATA`
  - Leave False. Publishing is the pipeline's job.

* **GH_DATA_REPO_PAT** - PAT token to the GitHub repository that stores the data.
  - Example: `"github_pat_XXXXXXXXXXXXXXXX"`
  - Default: None - required when SHOULD_PUSH_DATA is True
  - Command line: `--gh-data-repo-pat`
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