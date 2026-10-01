#!/usr/bin/env python3
"""Group a parse log's warnings and errors into a short triage report.

A patch-day parse can emit thousands of WARNING lines that are really a dozen
distinct issues (one message repeated per module, per level, ...). This reads a
parse log - the pipeline's tee (/srv/dev/wrf/logs/<run>/NN-parse.log) or a
scratch parse (tools/patch_day.sh parse) - and collapses it into groups, in
triage order:

  error             logger.error / logger.critical lines. Parse kept going, but
                    something was elevated as needing attention.
  warning           Any other logger.warning: an existing parser check tripped
                    (e.g. analysis:get_ability_stat "index out of range"). These
                    are the likely regressions - existing logic vs. new data.
  unknown-property  process_key_to_parser_function met a key its map doesn't
                    list: new game data to parse or skip.

Each group gets a count, examples, and the export JSON files it points at
(resolved like the parser / asset viewer do), so a human or agent can open the
right slice of the export instead of reading the whole log. With a baseline log
(by default the newest earlier *completed* pipeline parse), groups that were not
present there are marked NEW.

The report is written as markdown to reports/<name>.md in this repo (gitignored)
and copied to reports/latest.md, for VS Code's markdown preview (Ctrl+Shift+V;
the preview refreshes when the file is rewritten). Links in it open the parser
source at the owning line and the export JSON in the editor.

Decisions: every group has a stable id (u-/w-/e- + 8 hex). The report keeps
decisions/<version>.json (gitignored - local only) in sync: new groups are added
as "undecided"; the user (or Claude, on the user's word) fills in proposal /
reason and moves status through proposed -> approved | deferred. The script
only moves approved -> done when a newer *completed* parse no longer has the
group (and done -> approved if a newer one has it again). Decisions for the
same id in other versions' files show up as "previously". The report renders
all of it, so reports/latest.md doubles as the patch's progress tracker.

Usage:
    python tools/warning_report.py                          # latest pipeline run
    python tools/warning_report.py /srv/dev/wrf/logs/2026-09-29_022234
    python tools/warning_report.py /srv/dev/wrf/dev/logs/latest.log --no-baseline
    python tools/warning_report.py --stdout                 # print instead of writing
    python tools/warning_report.py --no-decisions           # don't read/update decisions/
    python tools/warning_report.py --json > report.json

Exit code: 0 = no groups, 1 = at least one group, 2 = bad input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

REPO_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_DIR / "reports"
DECISIONS_DIR = REPO_DIR / "decisions"
VERSION_RE = r"\d{4}-\d\d-\d\d(?:-\d+)?"
STATUSES = ("undecided", "proposed", "approved", "deferred", "done")
WRF_ROOT = Path(os.environ.get("WRF_ROOT", "/srv/dev/wrf"))
PIPELINE_LOG_ROOT = WRF_ROOT / "logs"
EXPORTS_ROOT = WRF_ROOT / "data" / "exports"
GAME_NAME = "WRFrontiers"
VIEWER_URL = "http://127.0.0.1:8765/"
# Printed by src/run.py when a parse runs to completion.
FINISHED_MARKER = "WRFrontiersDB-Parser@run.py finished"

# "[<timestamp> | ]LEVEL | module:function:line - message"
LINE_RE = re.compile(
    r"^(?:\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(?:\.\d+)? \| )?"
    r"(?P<level>TRACE|DEBUG|INFO|SUCCESS|WARNING|ERROR|CRITICAL)\s*\| "
    r"(?P<loc>\S+) - (?P<msg>.*)$"
)
# src/utils.py process_key_to_parser_function. Also matches the pre-2026-09-29
# format ("None None" owner, no [parser: ...] suffix).
UNKNOWN_RE = re.compile(
    r"^Warning: (?P<owner>.+?) has unknown property: '(?P<key>[^']*)' of value '(?P<value>.*?)'"
    r"(?:\s+in (?P<desc>.+?))?(?:\s+\[parser: (?P<parser>[^\]]+)\])?\s*$"
)
OBJECT_PATH_RE = re.compile(r"/Game/[^'\"\s,}]+")
ID_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*\.\d+\b")
LEVELS = ("CRITICAL", "ERROR", "WARNING")
KIND_ORDER = {"error": 0, "warning": 1, "unknown-property": 2}
MAX_DETAIL_LINES = 12


# ---------------------------------------------------------------- log reading

def resolve_log(arg: str | None) -> Path:
    """A log file, a pipeline run dir (-> its NN-parse.log), or None (-> latest run)."""
    if arg is None:
        runs = sorted(p for p in PIPELINE_LOG_ROOT.glob("*/") if _parse_log_in(p))
        if not runs:
            raise SystemExit(f"no pipeline run with a parse log under {PIPELINE_LOG_ROOT}")
        return _parse_log_in(runs[-1])
    path = Path(arg)
    if path.is_dir():
        found = _parse_log_in(path)
        if not found:
            raise SystemExit(f"no *-parse.log in {path}")
        return found
    if not path.is_file():
        raise SystemExit(f"log not found: {path}")
    return path


def _parse_log_in(run_dir: Path) -> Path | None:
    logs = sorted(run_dir.glob("*-parse.log"))
    return logs[-1] if logs else None


def default_baseline(log: Path) -> Path | None:
    """Newest completed pipeline parse log older than `log` (not `log` itself)."""
    candidates = []
    for run_dir in PIPELINE_LOG_ROOT.glob("*/"):
        cand = _parse_log_in(run_dir)
        if cand is None or cand.resolve() == log.resolve():
            continue
        if cand.stat().st_mtime >= log.stat().st_mtime:
            continue
        candidates.append(cand)
    for cand in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
        if _completed(cand):
            return cand
    return None


def _completed(log: Path) -> bool:
    with log.open(encoding="utf-8", errors="replace") as fh:
        return any(FINISHED_MARKER in line for line in fh)


def read_records(log: Path):
    """Yield (level, loc, msg, detail_lines) for WARNING-and-above records."""
    current = None
    with log.open(encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            m = LINE_RE.match(line)
            if m:
                if current:
                    yield current
                current = None
                if m["level"] in LEVELS:
                    current = (m["level"], m["loc"], m["msg"], [])
            elif current is not None and line.strip() and len(current[3]) < MAX_DETAIL_LINES:
                current[3].append(line)  # traceback / multi-line message continuation
    if current:
        yield current


# ------------------------------------------------------------------- grouping

def normalize(msg: str) -> str:
    """Collapse the varying parts of a message so repeats group together."""
    msg = OBJECT_PATH_RE.sub("<path>", msg)
    msg = re.sub(r"OBJID_\w+::[\w.]+", "<ref>", msg)
    msg = ID_RE.sub("<id>", msg)
    msg = re.sub(r"(?<![\w<])-?\d+(?:\.\d+)?(?![\w>])", "<n>", msg)
    return msg


def _loc_without_line(loc: str) -> str:
    return re.sub(r":\d+$", "", loc)


def _ownerless(key: tuple) -> tuple:
    """An unknown-property key with the owner blanked, to match baseline logs in
    the older format that could not name the owner ("None None")."""
    if key[0] == "unknown-property":
        return (key[0], "(unknown owner)") + key[2:]
    return key


def group_records(log: Path, max_examples: int) -> "OrderedDict[tuple, dict]":
    groups: "OrderedDict[tuple, dict]" = OrderedDict()
    for level, loc, msg, detail in read_records(log):
        um = UNKNOWN_RE.match(msg) if level == "WARNING" else None
        if um:
            owner = um["owner"].strip()
            if owner in ("None None", "(no parse object)"):
                owner_class, owner_id = "(unknown owner)", None
            else:
                owner_class, _, owner_id = owner.partition(" ")
            desc = (um["desc"] or "").strip() or None
            key = ("unknown-property", owner_class, desc, um["key"])
            g = groups.get(key)
            if g is None:
                g = groups[key] = {
                    "kind": "unknown-property",
                    "title": f"{owner_class}{' / ' + desc if desc else ''}: '{um['key']}'",
                    "property": um["key"],
                    "owner_class": owner_class,
                    "context": desc,
                    "parser": um["parser"],
                    "count": 0,
                    "owners": [],
                    "examples": [],
                }
            if owner_id and owner_id not in g["owners"] and len(g["owners"]) < max_examples:
                g["owners"].append(owner_id)
            value = um["value"]
        else:
            kind = "error" if level in ("ERROR", "CRITICAL") else "warning"
            template = normalize(msg)
            key = (kind, _loc_without_line(loc), template)
            g = groups.get(key)
            if g is None:
                g = groups[key] = {
                    "kind": kind,
                    "level": level,
                    "title": f"{_loc_without_line(loc)}: {template}",
                    "logged_at": loc,
                    "count": 0,
                    "ids": [],
                    "examples": [],
                    "detail": detail,
                }
            for obj_id in ID_RE.findall(msg):
                if obj_id not in g["ids"] and len(g["ids"]) < max_examples:
                    g["ids"].append(obj_id)
            value = msg
        g["count"] += 1
        if len(g["examples"]) < max_examples and value not in g["examples"]:
            g["examples"].append(value)
    return groups


# ------------------------------------------------------- export file lookups

class ExportIndex:
    """Resolve object ids and /Game/ object paths to files in an export tree."""

    def __init__(self, export_dir: Path):
        self.export_dir = export_dir
        self.by_stem: dict[str, list[str]] = {}
        self.by_lower_rel: dict[str, str] = {}
        for root, _dirs, files in os.walk(export_dir):
            for name in files:
                if not name.endswith(".json"):
                    continue
                rel = os.path.relpath(os.path.join(root, name), export_dir).replace(os.sep, "/")
                self.by_stem.setdefault(name[:-5].lower(), []).append(rel)
                self.by_lower_rel[rel.lower()] = rel

    def for_id(self, obj_id: str) -> list[str]:
        stem, _, index = obj_id.rpartition(".")
        if not stem:
            stem, index = obj_id, "0"
        return [f"{rel}#{index}" for rel in self.by_stem.get(stem.lower(), [])[:3]]

    def for_object_path(self, object_path: str) -> str | None:
        base, _, index = object_path.partition(".")
        rel = base.replace("/Game/", f"{GAME_NAME}/Content/", 1).lstrip("/") + ".json"
        real = self.by_lower_rel.get(rel.lower())
        if real is None:
            return None
        index = index.split(".")[-1] if index else "0"
        return f"{real}#{index if index.isdigit() else 0}"


def attach_files(groups, index: ExportIndex | None) -> None:
    for g in groups.values():
        files: list[str] = []
        if index is not None:
            ids = g.get("owners") or g.get("ids") or []
            for obj_id in ids:
                files.extend(f for f in index.for_id(obj_id) if f not in files)
            for example in g["examples"]:
                for object_path in OBJECT_PATH_RE.findall(example):
                    f = index.for_object_path(object_path)
                    if f and f not in files:
                        files.append(f)
        g["files"] = files[:6]


def log_version(log: Path) -> str | None:
    """The patch version a log belongs to: <version>.log (parser's own log),
    parse-<version>-<stamp>.log (patch_day.sh), or version= in the run's run.log."""
    m = re.match(rf"^(?:parse-)?({VERSION_RE})(?:-\d{{8}}_\d{{6}})?$", log.stem)
    if m:
        return m[1]
    run_log = log.parent / "run.log"
    if run_log.is_file():
        m = re.search(rf"version=({VERSION_RE})", run_log.read_text(errors="replace"))
        if m:
            return m[1]
    return None


def default_export_dir(log: Path) -> Path | None:
    """exports/<version> for the log's version, else the newest one."""
    version = log_version(log)
    if version and (EXPORTS_ROOT / version).is_dir():
        return EXPORTS_ROOT / version
    versions = sorted(p for p in EXPORTS_ROOT.glob("*") if p.is_dir())
    return versions[-1] if versions else None


# ------------------------------------------------------------------ decisions

def _hash_id(kind: str, parts: tuple) -> str:
    text = "\x1f".join("" if p is None else str(p) for p in parts)
    return f"{kind[0]}-{hashlib.sha1(text.encode()).hexdigest()[:8]}"


def assign_ids(groups) -> None:
    """Stable ids. Unknown-property ids leave out the owner class, so a group keeps
    its id across the old ("None None") and new warning formats; only if two owner
    classes share context + property in one log does the owner disambiguate."""
    taken: set[str] = set()
    for key, g in groups.items():
        kind = key[0]
        gid = _hash_id(kind, _ownerless(key) if kind == "unknown-property" else key)
        if gid in taken:
            gid = _hash_id(kind, key)
        taken.add(gid)
        g["id"] = gid


def _log_time(log: Path) -> str:
    return datetime.fromtimestamp(log.stat().st_mtime).isoformat(timespec="seconds")


def previous_decision(gid: str, version: str) -> dict | None:
    """The newest decision for gid in an earlier version's decisions file."""
    for path in sorted(DECISIONS_DIR.glob("*.json"), reverse=True):
        if path.stem >= version:
            continue
        try:
            entry = json.loads(path.read_text(encoding="utf-8")).get("groups", {}).get(gid)
        except (OSError, ValueError):
            continue
        if entry and entry.get("status") != "undecided":
            return {"version": path.stem, **{k: entry.get(k, "") for k in ("status", "proposal", "reason")}}
    return None


def sync_decisions(path: Path, version: str, groups, log: Path) -> dict:
    """Add new groups as undecided and move approved <-> done; returns the file's data.

    Transitions only follow logs newer than the evidence already recorded, so
    re-running the report on an old log never marks anything done or undoes it.
    """
    data = {"version": version, "groups": {}}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise SystemExit(f"decisions file is not valid JSON - fix it first: {path}: {exc}")
    entries = data.setdefault("groups", {})
    log_time = _log_time(log)
    completed = _completed(log)
    changed = not path.is_file()

    for g in groups.values():
        entry = entries.get(g["id"])
        if entry is None:
            entry = entries[g["id"]] = {
                "title": g["title"],
                "kind": g["kind"],
                "status": "undecided",
                "proposal": "",
                "reason": "",
                "where": g.get("parser") or g.get("logged_at") or "",
                "confidence": "",
                "notes": "",
                "last_seen": log_time,
            }
            previous = previous_decision(g["id"], version)
            if previous:
                entry["previous"] = previous
            changed = True
        elif log_time > entry.get("last_seen", ""):
            entry["last_seen"] = log_time
            if entry.get("status") == "done" and log_time > entry.get("done_at", ""):
                entry["status"] = "approved"
                entry["notes"] = f"{entry.get('notes', '')} [reappeared in {log.name}]".strip()
            changed = True
        g["decision"] = entry

    present = {g["id"] for g in groups.values()}
    if completed:
        for gid, entry in entries.items():
            if (gid not in present and entry.get("status") == "approved"
                    and log_time > entry.get("last_seen", "")):
                entry["status"] = "done"
                entry["done_at"] = log_time
                changed = True

    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(path)
    return data


# -------------------------------------------------------------------- output

def _clip(text: str, width: int) -> str:
    text = text.replace("\n", " ").replace("`", "'")
    return text if len(text) <= width else text[: width - 1] + "…"


def _cell(text: str, width: int) -> str:
    """_clip for a markdown table cell."""
    return _clip(text, width).replace("|", "\\|")


def report_path(log: Path) -> Path:
    """reports/pipeline_<run-dir>.md for a pipeline run, else reports/<log stem>.md."""
    try:
        log.resolve().relative_to(PIPELINE_LOG_ROOT.resolve())
        return REPORTS_DIR / f"pipeline_{log.parent.name}.md"
    except ValueError:
        return REPORTS_DIR / f"{log.stem}.md"


class Linker:
    """Markdown links to local files: relative to the report's dir when writing a
    file (VS Code's preview opens them in the editor), absolute for stdout."""

    def __init__(self, base_dir: Path | None):
        self.base_dir = base_dir
        self._modules: dict[str, Path] | None = None

    def href(self, target: Path, line: int | None = None) -> str:
        path = os.path.relpath(target, self.base_dir) if self.base_dir else str(target)
        return quote(path.replace(os.sep, "/")) + (f"#L{line}" if line else "")

    def file(self, label: str, target: Path, line: int | None = None) -> str:
        return f"[{label}]({self.href(target, line)})"

    def parser_location(self, location: str) -> str:
        """'src/x.py:12 func' (unknown-property) -> link to the line."""
        m = re.match(r"^(?P<file>\S+?):(?P<line>\d+)(?: (?P<func>\S+))?$", location)
        if not m:
            return f"`{location}`"
        link = self.file(f"{m['file']}:{m['line']}", REPO_DIR / m["file"], int(m["line"]))
        return f"{link} `{m['func']}`" if m["func"] else link

    def logged_at(self, loc: str) -> str:
        """'module:function:line' (loguru) -> link to the line, if the module is in src/."""
        module, _, rest = loc.partition(":")
        func, _, line = rest.rpartition(":")
        target = self._module_file(module)
        if target is None or not line.isdigit():
            return f"`{loc}`"
        return f"{self.file(f'{target.relative_to(REPO_DIR)}:{line}', target, int(line))} `{func}`"

    def _module_file(self, module: str) -> Path | None:
        if self._modules is None:
            self._modules = {}
            for path in sorted((REPO_DIR / "src").rglob("*.py")):
                self._modules.setdefault(path.stem, path)
        return self._modules.get(module.rpartition(".")[2])


def render_markdown(log: Path, baseline: Path | None, export_dir: Path | None, groups, total: int,
                    linker: Linker, decisions: dict | None = None, decisions_path: Path | None = None) -> str:
    ordered = sorted(groups.values(), key=lambda g: (KIND_ORDER[g["kind"]], -g["count"]))
    by_kind = {k: [g for g in ordered if g["kind"] == k] for k in KIND_ORDER}
    for n, g in enumerate(ordered, 1):
        g["n"] = n
    new_count = sum(1 for g in ordered if g.get("new"))

    out = ["# Parse warning report", "",
           f"**{total}** WARNING+ lines -> **{len(groups)}** groups: "
           + ", ".join(f"{len(by_kind[k])} {k}" for k in KIND_ORDER)
           + (f"; **{new_count} NEW** vs baseline" if baseline else ""), "",
           f"- log: {linker.file(log.name, log)} (`{log}`)",
           f"- baseline: {linker.file(baseline.name, baseline)} (`{baseline}`)" if baseline
           else "- baseline: none (NEW markers unavailable)",
           f"- export dir: `{export_dir}`" if export_dir else "- export dir: none (files not resolved)",
           f"- generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
    entries = (decisions or {}).get("groups", {})
    if decisions is not None and decisions_path is not None:
        by_status = {st: sum(1 for e in entries.values() if e.get("status") == st) for st in STATUSES}
        out.append(f"- decisions: {linker.file(decisions_path.name, decisions_path)} - "
                   + ", ".join(f"{n} {st}" for st, n in by_status.items() if n))
    out.append("")
    if not groups:
        out += ["**Clean: no warnings or errors.**", ""]
    elif decisions is not None:
        out += ["| # | id | kind | group | count | status | proposal | |",
                "| ---: | --- | --- | --- | ---: | --- | --- | --- |"]
        for g in ordered:
            d = g.get("decision", {})
            out.append(f"| {g['n']} | `{g['id']}` | {g['kind']} | {_cell(g['title'], 90)} | {g['count']} "
                       f"| {d.get('status', '')} | {_cell(d.get('proposal', ''), 60)} | {'NEW' if g.get('new') else ''} |")
    else:
        out += ["| # | kind | group | count | |", "| ---: | --- | --- | ---: | --- |"]
        for g in ordered:
            out.append(f"| {g['n']} | {g['kind']} | {_cell(g['title'], 110)} | {g['count']} | {'NEW' if g.get('new') else ''} |")
    out.append("")

    for kind in KIND_ORDER:
        if not by_kind[kind]:
            continue
        out += [f"## {kind} ({len(by_kind[kind])})", ""]
        for g in by_kind[kind]:
            new = " - NEW" if g.get("new") else ""
            out += [f"### {g['n']}. {_clip(g['title'], 160)}{new}", ""]
            out.append(f"- id: `{g['id']}` - count: **{g['count']}**")
            d = g.get("decision")
            if d is not None:
                line = f"- decision: **{d.get('status', '?')}**"
                if d.get("proposal"):
                    line += f" - {_clip(d['proposal'], 200)}"
                if d.get("reason"):
                    line += f" ({_clip(d['reason'], 200)})"
                out.append(line)
                if d.get("notes"):
                    out.append(f"- notes: {_clip(d['notes'], 300)}")
                prev = d.get("previous")
                if prev:
                    out.append(f"- previously ({prev['version']}): {prev.get('status', '')}"
                               + (f" - {_clip(prev['proposal'], 160)}" if prev.get("proposal") else ""))
            if kind == "unknown-property":
                if g.get("parser"):
                    out.append(f"- parser: {linker.parser_location(g['parser'])}")
                if g["owners"]:
                    out.append(f"- owners: {', '.join(f'`{o}`' for o in g['owners'])}")
                out.append(f"- value: `{_clip(g['examples'][0], 240)}`")
            else:
                out.append(f"- logged at: {linker.logged_at(g['logged_at'])} ({g['level']})")
                if g["ids"]:
                    out.append(f"- ids: {', '.join(f'`{i}`' for i in g['ids'])}")
                for ex in g["examples"]:
                    out.append(f"- example: `{_clip(ex, 240)}`")
                if g.get("detail"):
                    out += ["", "```text", *g["detail"][:MAX_DETAIL_LINES], "```"]
            for f in g["files"]:
                rel, _, index = f.partition("#")
                label = f"{rel.rsplit('/', 1)[-1]}#{index or 0}"
                target = linker.file(label, export_dir / rel) if export_dir else f"`{f}`"
                out.append(f"- export: {target} - [viewer]({VIEWER_URL}#{quote(f)})")
            out.append("")

    present = {g["id"] for g in ordered}
    absent = [(gid, e) for gid, e in entries.items() if gid not in present]
    if absent:
        out += ["## Not in this log", "",
                "Decided groups this parse no longer produces (done = fixed and confirmed by a newer completed parse).", "",
                "| id | group | status | proposal |", "| --- | --- | --- | --- |"]
        for gid, e in absent:
            out.append(f"| `{gid}` | {_cell(e.get('title', ''), 90)} | {e.get('status', '')} | {_cell(e.get('proposal', ''), 60)} |")
        out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log", nargs="?", help="parse log file or pipeline run dir (default: latest pipeline run)")
    ap.add_argument("--baseline", help="log to compare against for NEW markers (default: newest earlier completed pipeline parse)")
    ap.add_argument("--no-baseline", action="store_true", help="skip NEW detection")
    ap.add_argument("--export-dir", help="export tree to resolve files in (default: exports/<version> for the log)")
    ap.add_argument("--no-resolve", action="store_true", help="don't index the export tree")
    ap.add_argument("--max-examples", type=int, default=3)
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    ap.add_argument("--summary", action="store_true", help="print only the one-line group counts")
    ap.add_argument("--stdout", action="store_true", help="print the markdown instead of writing reports/")
    ap.add_argument("--out", help="write the markdown here instead of reports/<name>.md (no latest.md copy)")
    ap.add_argument("--version", help="patch version (default: from the log name / run.log)")
    ap.add_argument("--decisions", help="decisions file (default: decisions/<version>.json)")
    ap.add_argument("--no-decisions", action="store_true", help="don't read or update a decisions file")
    args = ap.parse_args()

    log = resolve_log(args.log)
    groups = group_records(log, args.max_examples)
    assign_ids(groups)
    total = sum(g["count"] for g in groups.values())

    baseline = None
    if not args.no_baseline:
        baseline = Path(args.baseline) if args.baseline else default_baseline(log)
        if baseline is not None:
            if not baseline.is_file():
                print(f"baseline not found: {baseline}", file=sys.stderr)
                return 2
            known = set(group_records(baseline, 1).keys())
            for key, g in groups.items():
                g["new"] = key not in known and _ownerless(key) not in known

    counts = {k: sum(1 for g in groups.values() if g["kind"] == k) for k in KIND_ORDER}
    if args.summary:
        new = sum(1 for g in groups.values() if g.get("new"))
        print(f"{total} WARNING+ lines -> {len(groups)} groups ("
              + ", ".join(f"{v} {k}" for k, v in counts.items())
              + (f"; {new} NEW vs baseline" if baseline else "") + ")")
        return 1 if groups else 0

    decisions = decisions_path = None
    if not args.no_decisions:
        version = args.version or log_version(log)
        if args.decisions:
            decisions_path = Path(args.decisions).resolve()
        elif version:
            decisions_path = DECISIONS_DIR / f"{version}.json"
        else:
            print("no patch version for this log - decisions skipped (pass --version)", file=sys.stderr)
        if decisions_path is not None:
            decisions = sync_decisions(decisions_path, version or decisions_path.stem, groups, log)

    export_dir = None
    if not args.no_resolve:
        export_dir = Path(args.export_dir) if args.export_dir else default_export_dir(log)
    index = ExportIndex(export_dir) if export_dir and export_dir.is_dir() else None
    attach_files(groups, index)

    if args.json:
        print(json.dumps({
            "log": str(log),
            "baseline": str(baseline) if baseline else None,
            "export_dir": str(export_dir) if index else None,
            "total_lines": total,
            "counts": counts,
            "groups": sorted(groups.values(), key=lambda g: (KIND_ORDER[g["kind"]], -g["count"])),
        }, indent=2))
    elif args.stdout:
        print(render_markdown(log, baseline, export_dir if index else None, groups, total, Linker(None),
                              decisions, decisions_path), end="")
    else:
        out = Path(args.out).resolve() if args.out else report_path(log)
        out.parent.mkdir(parents=True, exist_ok=True)
        text = render_markdown(log, baseline, export_dir if index else None, groups, total, Linker(out.parent),
                               decisions, decisions_path)
        out.write_text(text, encoding="utf-8")
        if not args.out:
            (REPORTS_DIR / "latest.md").write_text(text, encoding="utf-8")
        print(f"report: {out}" + ("" if args.out else f" (and {REPORTS_DIR / 'latest.md'})"))
        print(text.split("\n", 3)[2])  # the counts line
    return 1 if groups else 0


if __name__ == "__main__":
    raise SystemExit(main())
