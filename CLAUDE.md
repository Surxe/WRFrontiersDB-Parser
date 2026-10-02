# WRFrontiersDB-Parser - agent context

Parses the Exporter's JSON dump of War Robots Frontiers into the objects that
WRFrontiersDB-Data publishes and WRFrontiersDB-Site renders. On the home-server
it runs as the PARSE/PUSH stage of **WRFrontiersDB-Orchestrator** after every
game patch. Nearly every patch adds data the parser has not seen, so this is the
one repo that changes on every patch; the human process for that is
`WRFrontiersDB-Orchestrator/PATCH_DAY.md`, and the agent process is the
`patch-warnings` skill (`.claude/skills/patch-warnings/SKILL.md`).

## Two checkouts - never develop in the pipeline's

| Path | Role |
| --- | --- |
| `/srv/dev/repos/WRFrontiersDB-Parser` | **Pipeline clone.** Always `main`, always clean, no `.env` (the orchestrator passes every option as an argument). The orchestrator runs whatever is checked out here, so never edit it; it only moves by `git pull --ff-only` after a PR merges. |
| `/srv/dev/repos/WRFrontiersDB-Parser-dev` | **Dev worktree** (`git worktree` of the same repo). Patch work happens here on a `patch/<version>` branch, with its own `.venv` and a `.env` written by `tools/patch_day.sh init`. It cannot check out `main` (the pipeline clone has it); park it detached at `origin/main` between patches. |

Other WRF repos (Orchestrator, Exporter, Site, Data) are developed on the home
PC; patch-day work only touches this one.

## Layout

- `src/run.py` - entry point; options from args > `.env` > defaults (`options_schema.py`, see README).
- `src/parse/parse.py` - parse order, then `to_file()` for every object type.
- `src/parse/parsers/<type>.py` - one parser per object type. Each builds a
  `key_to_parser_function` map and hands it to `process_key_to_parser_function`.
- `src/utils.py` - `process_key_to_parser_function`, path/asset helpers.
- `src/parse/analysis.py`, `src/parse/enrichment.py` - derived data after parsing.
- `src/push/push.py` - push to the data repo (the pipeline does this; you never do).
- `tools/` - `patch_day.sh`, `warning_report.py`, `asset-viewer/`.

## Key maps: parse or skip

Every property of a parsed struct must appear in its map, or it logs an
unknown-property warning. Map values (full syntax in the
`process_key_to_parser_function` docstring):

- `"value"` - store as-is (snake_case attribute by default).
- a function (`p_actor_class`, `parse_colon_colon`, ...) - parse via that function.
- `(function, "name")` or a config dict - custom target / `DICT_ENTRY` placement.
- `None` - **deliberately skipped. Always add a `#reason` comment** (`#vfx`,
  `#audio`, `#voice line`, `#dupe data`, ...). These comments are the record of
  every past skip decision.

Decision rules, as established in past patch PRs:

- FX, VFX, sound/Wwise events, voice lines, meshes, materials, UI/targeting
  markers -> `None` with a reason.
- Gameplay scalars (damage, radius, duration, multipliers, counts, flags that
  change behaviour) -> `"value"`.
- References to buffs/actors (`*BuffClass`, `*ActorClass`, `WeaponModule`, ...)
  -> the matching parser (`p_actor_class` etc.), so their gameplay data is
  followed. Follow the reference in the export before deciding; an "FX-only"
  buff or an empty generic asset is a skip.
- Parameter names that only feed a VFX/material (`...Param` strings) -> `None`.
- When a new struct carries gameplay data under a new key, add a sub-parser
  next to its siblings rather than storing the raw dict.
- Unsure -> investigate in the export and ask; do not guess.

## Logging levels

Only an exception stops the pipeline (and the data push). Everything else is
published, and the level is how it gets noticed: `raise` if continuing would
publish garbage, `logger.error` if output is knowingly wrong/incomplete in a way
that matters, `logger.warning` for unhandled-but-harmless. Unknown properties
log at the custom `UNKNOWN_PROPERTY` level (no 31, just above WARNING's 30), so
they are counted apart from real warnings. Full rules:
`STANDARDS.md` -> *Choosing a Log Level*. When fixing a warning that turned out to
hide real data loss, elevate that call to `logger.error`.

The unknown-property message names the owning object and the parser code that
owns the key map:

```
UNKNOWN_PROPERTY | utils:process_key_to_parser_function:470 - Ability BP_Module_Angler_Torso.1 has unknown property: 'ActorsType' of value '1' in ConfirmationAction [parser: src/parse/parsers/ability.py:520 _p_targeting_action]
```

Module-level `p_*` helpers have no object of their own; the owner is then the
innermost `ParseObject` being parsed (tracked by `utils.parse_context`), or
`(no parse object)`. `tools/warning_report.py` parses this format - change both
together (tests: `tests/test_utils/test_process_key_to_parser_function.py`).

## Patch-day tools

All from the dev worktree:

```bash
tools/patch_day.sh init <version>    # point the loop at a patch (writes .env, resets review repo)
tools/patch_day.sh parse             # scratch parse -> /srv/dev/wrf/dev/parsed, sync review repo, write report
tools/patch_day.sh report            # grouped warnings for the latest scratch parse -> reports/latest.md
tools/patch_day.sh checkpoint "msg"  # accept a step: commit parser code (patch/<version>) + review repo, linked
tools/patch_day.sh status            # checkpoints + total diff vs pipeline baseline
tools/patch_day.sh viewer            # asset viewer for the patch's export, http://127.0.0.1:8765/

.venv/bin/python tools/warning_report.py [LOG|RUN_DIR]   # default: latest pipeline run; --stdout to print
```

- The **review repo** `/srv/dev/wrf/dev/parsed-review` is a scratch git repo:
  commit `baseline` = the pipeline's parse of the patch, working tree = the latest
  scratch parse. `git -C /srv/dev/wrf/dev/parsed-review diff` (or VS Code Source
  Control with the folder in the workspace) shows exactly what a parser change
  did to the output.
- `warning_report.py` groups a log into `error` / `warning` / `unknown-property`
  groups with counts, example values, the parser location, the export files to
  open, and viewer links. It marks groups NEW vs. the previous completed pipeline
  parse when one exists. It writes markdown to `reports/<name>.md` (gitignored;
  `pipeline_<run>.md` or `parse-<version>-<stamp>.md`) and copies it to
  `reports/latest.md` - the user keeps that open in VS Code's preview, and its links
  open the parser line and the export JSON. Read the file (it's small) rather than
  re-running with `--stdout`, so you and the user look at the same report.
- **Decisions** live in `decisions/<version>.json` - **gitignored, local only;
  never commit or push them** (the user may back them up separately). The report
  keeps the file in sync: each group (stable id `u-`/`w-`/`e-` + 8 hex) gets an
  entry, new ones as `undecided`; `proposal` / `reason` / `confidence` / `status`
  are written by you or the user (`proposed` -> `approved` | `deferred`), and the
  script moves `approved` -> `done` once a newer completed parse no longer has the
  group. Earlier versions' decisions for the same id show as `previous`. The
  report renders status + proposal per group, so `reports/latest.md` is also the
  patch's progress tracker. `--no-decisions` skips all of it.
- Exports live at `/srv/dev/wrf/data/exports/<version>/WRFrontiers/Content/...`
  and the pipeline's parsed output at `/srv/dev/wrf/data/parsed/<version>/`; the
  pipeline keeps the 2 newest versions of both, so the previous patch's export and
  parsed output are there for comparison (except after its first run on this box).
  An object id `Foo.1` is element `[1]` of `Foo.json`.

## Rules

- **Read logs and exports in slices** - `warning_report.py`, `grep -n`, `jq`,
  `sed -n`. A parse log is ~5 MB and export files can be large; never read one whole.
- Scratch parses only (`tools/patch_day.sh parse`). Never run with
  `--should-push-data true`; publishing is the pipeline's job.
- Tests: `.venv/bin/python -m unittest discover -s tests -p "test_*.py"`. The
  suite passes clean on `main`; any failure is a regression. A new test directory
  needs an `__init__.py` or discover skips it.
- Follow `STANDARDS.md` naming (`*_ref`, `*_refs`, `*_id`, `*_dir`, `*_file`).
- Branch per patch: `patch/<version>`; PR body covering the properties
  handled, what was skipped and why, fixes, how it was verified).
