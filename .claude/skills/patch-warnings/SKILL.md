---
name: patch-warnings
description: Patch-day parser work on the home-server - triage a patch's parse warnings/errors, agree parse/skip/fix decisions with Ethan, implement them in the parser dev worktree, verify with scratch parses + the parsed-output diff, and open the PR. Use when the user runs /patch-warnings [version], or asks to handle / triage / fix the parser warnings from a patch-day run.
---

# patch-warnings

Human-in-the-loop handling of a patch's parse warnings. Claude does the
legwork (grouping, reading the export, proposing, implementing, verifying);
Ethan makes the calls at two gates and reviews the output diff in VS Code. The
human side of the same process is `WRFrontiersDB-Orchestrator/PATCH_DAY.md`;
repo context is this repo's `CLAUDE.md` (read it first if you haven't).

Argument: the patch version (`yyyy-mm-dd[-N]`). If omitted, use the version of
the latest pipeline run: `grep -o 'version=[^ ]*' /srv/dev/wrf/logs/<latest>/run.log`.

Everything runs in the **dev worktree** `/srv/dev/repos/WRFrontiersDB-Parser-dev`.
Never edit the pipeline clone `/srv/dev/repos/WRFrontiersDB-Parser`, never push
data, never read a whole log or export file (use the report, `grep -n`, `jq`,
`sed -n`).

## Phase 0 - Set up

1. Worktree state: `git -C /srv/dev/repos/WRFrontiersDB-Parser-dev status -sb`.
   - Uncommitted changes that aren't this patch's -> stop and ask.
   - Already on `patch/<version>` -> resuming; skip to the phase the state implies
     (`tools/patch_day.sh status` shows checkpoints).
   - Otherwise: `git fetch origin && git switch -c patch/<version> origin/main`
     (if that branch exists already, switch to it instead).
2. If `/srv/dev/wrf/dev/VERSION` is not `<version>`: `tools/patch_day.sh init <version>`.
   Do not re-init a version that has checkpoints - it resets the review repo.
3. If `requirements.txt` changed since the venv was built, `.venv/bin/pip install -r requirements.txt`.

## Phase 1 - Triage report

```bash
.venv/bin/python tools/warning_report.py /srv/dev/wrf/logs/<run-dir>
```

(`<run-dir>` = the pipeline run for this version; no argument = latest run.)
Show Ethan the group count line and the headings. If there are no groups, say so
and stop - nothing to do.

Then a **sanity scratch parse** before any edits: `tools/patch_day.sh parse`.
With no parser changes the review diff should be empty. If it isn't, the
pipeline's environment differs from the dev worktree's (e.g. the pipeline venv
missing a dependency - on 2026-09-29 a missing `zstandard` silently emptied every
model's `meshes`). Report that to Ethan as its own finding; it is fixed in the
pipeline's environment, not the parser. Checkpoint the state afterwards
(`tools/patch_day.sh checkpoint "sanity parse"`) so later diffs show only parser
changes.

## Phase 2 - Investigate each group

Order: `error`, then `warning`, then `unknown-property`. For each group:

- **unknown-property**: open the owner's export slice (the report's `export:`
  lines; `Foo.json#1` = element `[1]`), e.g.
  `jq '.[1].Properties | keys' <file>` then `jq '.[1].Properties.<Key>' <file>`.
  Follow any `ObjectPath` the value holds to see what it points at (a buff with
  gameplay stats vs an FX-only asset). Open the parser at the report's
  `parser:` location and look at the sibling keys and their skip comments.
  Classify with the decision rules in `CLAUDE.md` (*Key maps: parse or skip*).
- **warning / error**: read the code at `logged at`, then compare the new export
  with the previous patch's (`/srv/dev/wrf/data/exports/` keeps 2 versions) for
  one of the listed ids to find what changed in the data. Decide whether the
  parser logic needs fixing, and whether the log call should be elevated to
  `logger.error` (STANDARDS.md -> *Choosing a Log Level*): a warning that fires
  for many objects or drops published data is an error.

Also note anything suspicious you see while reading (e.g. data silently
dropped at DEBUG level) - it goes in the proposal as an extra row.

## Gate 1 - Decisions (stop here)

Present one table and **wait for Ethan's answer**. Do not edit code before it.
Example rows (illustrative, not real decisions):

| # | Group | Evidence (1 line) | Proposal | Where |
| --- | --- | --- | --- | --- |
| 1 | `get_ability_stat` out of range (1488) | chassis now have 1 scaler, index 1 asked | fix logic + elevate to error | analysis.py:810 |
| 4 | Ability/ActorClass `WeaponInfo` | TeslaFeed beam weapon ref | parse via `p_weapon_infos` | ability.py:1369 map |
| 10 | Ability/ActorClass `ConnectionOnInstigatorSoundEvent` | Wwise event | skip `#audio` | ability.py:1369 map |

Proposal is one of: `value`, `parse via <fn>` / `new sub-parser`, `skip #reason`,
`fix logic`, `elevate to error`, `needs Ethan` (say what you couldn't resolve).
Mark low-confidence rows. Ethan may approve, change rows, or defer some; carry
deferred rows into the PR body as open items.

## Phase 3 - Implement and verify

1. Make the approved changes in the dev worktree, following the map conventions
   (every `None` gets a `#reason`; sub-parsers next to their siblings; STANDARDS.md
   naming). Add or update a unit test when you change logic (not needed for
   plain map entries).
2. `tools/patch_day.sh parse` - it syncs the review repo and prints the group
   summary. `tools/patch_day.sh report` for details. NEW groups in a scratch
   report are ones your change introduced (the baseline is the pipeline's parse).
3. Iterate until every approved group is gone and nothing NEW appeared.
4. Tests: `.venv/bin/python -m unittest discover -s tests -p "test_*.py"`. Compare
   failures with `main`'s (some fail there already); no new failures.
5. Summarise the output change: `git -C /srv/dev/wrf/dev/parsed-review diff --stat`
   plus a few representative hunks (read them with `git diff -- <file> | head`).
   Check the new fields are present and nothing unrelated moved.

## Gate 2 - Output review (stop here)

Tell Ethan the review is ready: the `parsed-review` folder in VS Code's Source
Control shows the diff since the last checkpoint. Give your summary from step 5
and **wait**. On approval, `tools/patch_day.sh checkpoint "<what changed>"`. If he
asks for changes, go back to Phase 3.

## Phase 4 - PR

1. Commit on `patch/<version>` (one commit is fine; message `Parse <version>: <summary>`).
2. Open the PR with the `pr` skill (don't create another branch - you're on one).
   Title `Parse <version>: <summary>`; body in the style of #112:
   - **New properties handled** - per parser file: property -> how, one line each.
   - **Skipped** - property -> reason.
   - **Fixes** - logic changes and log-level elevations, with the cause.
   - **Open items** - deferred groups, pipeline-environment findings.
   - **Verified** - scratch parse exit 0, remaining groups (ideally 0), tests vs main,
     parsed-output diff summary.
3. Stop. Merging is Ethan's. After the merge, the next step is `/republish-patch
   <version>` in the Orchestrator repo - **not** `/merged`: it would try to check
   out `main` in this worktree, which the pipeline clone holds.
