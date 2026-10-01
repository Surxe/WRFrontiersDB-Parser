---
name: patch-warnings
description: Patch-day parser work on the home-server - triage a patch's parse warnings/errors, agree parse/skip/fix decisions with the user, implement them in the parser dev worktree, verify with scratch parses + the parsed-output diff, and open the PR. Use when the user runs /patch-warnings [version], or asks to handle / triage / fix the parser warnings from a patch-day run.
---

# patch-warnings

Human-in-the-loop handling of a patch's parse warnings. Claude does the
legwork (grouping, reading the export, proposing, implementing, verifying);
The user makes the calls at two gates and reviews the output diff in VS Code. The
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
It writes `reports/pipeline_<run-dir>.md` and `reports/latest.md` and prints the
path + group count line; read the report file. Point the user at
`reports/latest.md` (VS Code: open it, `Ctrl+Shift+V` for the preview) and give
the count line plus the group headings. If there are no groups, say so and stop -
nothing to do.

The report also creates `decisions/<version>.json` (gitignored, local only - never
commit it), with every group as an `undecided` entry keyed by its stable id
(`u-`/`w-`/`e-` + 8 hex, shown in the report). If an id was decided in an earlier
version's file, the entry carries it as `previous` - respect a past decision unless
the data changed, and say so when you diverge.

Then a **sanity scratch parse** before any edits: `tools/patch_day.sh parse`.
With no parser changes the review diff should be empty. If it isn't, the
pipeline's environment differs from the dev worktree's (e.g. the pipeline venv
missing a dependency - on 2026-09-29 a missing `zstandard` silently emptied every
model's `meshes`). Report that to the user as its own finding; it is fixed in the
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
- **warning / error**: read the code at `logged at`, then compare this patch
  with the previous one for one of the listed ids to find what changed: both the
  export (`/srv/dev/wrf/data/exports/<prev-version>/`) and the pipeline's parsed
  output (`/srv/dev/wrf/data/parsed/<prev-version>/`) are kept for the 2 newest
  versions. (On the pipeline's first run on this box there is no previous
  version yet.) Decide whether the
  parser logic needs fixing, and whether the log call should be elevated to
  `logger.error` (STANDARDS.md -> *Choosing a Log Level*): a warning that fires
  for many objects or drops published data is an error.

Also note anything suspicious you see while reading (e.g. data silently
dropped at DEBUG level) - it goes in the proposal as an extra row.

## Gate 1 - Decisions (stop here)

Write your proposals **into `decisions/<version>.json`**, one entry per group id.
Edit only these fields and keep the rest (the script owns `last_seen`,
`done_at`, `previous`):

```json
"u-29f0b7bf": {
  "title": "...", "kind": "unknown-property",
  "status": "proposed",
  "proposal": "parse via p_weapon_infos",
  "reason": "TeslaFeed beam weapon ref - carries the beam's damage stats",
  "where": "src/parse/parsers/ability.py:1369 p_actor_class",
  "confidence": "high",
  "notes": ""
}
```

`proposal` is one of: `value`, `parse via <fn>` / `new sub-parser`, `skip #reason`,
`fix logic`, `elevate to error`, `needs user` (say in `reason` what you couldn't
resolve). `confidence` is `high` or `low`. Extra findings that aren't a log group
(e.g. data silently dropped at DEBUG) go in chat and in the PR's open items - they
have no id.

Re-run the report (`.venv/bin/python tools/warning_report.py /srv/dev/wrf/logs/<run-dir>`)
so `reports/latest.md` shows the proposals in its table, then **stop and wait**.
Tell the user to review in the preview and decide, either by editing `status` in
the JSON (`approved` / `deferred`; they may also rewrite `proposal`) or by
answering in chat - then you set the statuses they gave. Do not edit code before
it. Statuses: `undecided` -> `proposed` (you) -> `approved` | `deferred` (the user)
-> `done` (set by the script, never by hand).

## Phase 3 - Implement and verify

1. Make the changes for entries with status `approved` (only those) in the dev worktree, following the map conventions
   (every `None` gets a `#reason`; sub-parsers next to their siblings; STANDARDS.md
   naming). Add or update a unit test when you change logic (not needed for
   plain map entries).
2. `tools/patch_day.sh parse` - it syncs the review repo and rewrites
   `reports/latest.md` for the scratch parse (the user's open preview refreshes).
   Read that file for details. NEW groups in a scratch
   report are ones your change introduced (the baseline is the pipeline's parse);
   they get `undecided` entries - propose for them and ask before acting.
   When a completed scratch parse no longer has an approved group, the script
   marks it `done` (and back to `approved` with a note if it reappears later).
3. Iterate until every approved entry is `done` and nothing NEW appeared.
4. Tests: `.venv/bin/python -m unittest discover -s tests -p "test_*.py"`. Compare
   failures with `main`'s (some fail there already); no new failures.
5. Summarise the output change: `git -C /srv/dev/wrf/dev/parsed-review diff --stat`
   plus a few representative hunks (read them with `git diff -- <file> | head`).
   Check the new fields are present and nothing unrelated moved.

## Gate 2 - Output review (stop here)

Tell the user the review is ready: the `parsed-review` folder in VS Code's Source
Control shows the diff since the last checkpoint. Give your summary from step 5
and **wait**. On approval, `tools/patch_day.sh checkpoint "<what changed>"`. If the
user asks for changes, go back to Phase 3.

## Phase 4 - PR

1. Commit on `patch/<version>` (one commit is fine; message `Parse <version>: <summary>`).
2. Open the PR with the `pr` skill (don't create another branch - you're on one).
   Title `Parse <version>: <summary>`; build the body from `decisions/<version>.json`
   (the file itself stays local) with these sections:
   - **New properties handled** - per parser file: property -> how, one line each.
   - **Skipped** - property -> reason.
   - **Fixes** - logic changes and log-level elevations, with the cause.
   - **Open items** - `deferred` entries (and anything still `proposed`/`undecided`),
     pipeline-environment findings.
   - **Verified** - scratch parse exit 0, remaining groups (ideally 0), tests vs main,
     parsed-output diff summary.
3. Stop. Merging is the user's. After the merge, the next step is `/republish-patch
   <version>` in the Orchestrator repo - **not** `/merged`: it would try to check
   out `main` in this worktree, which the pipeline clone holds.
