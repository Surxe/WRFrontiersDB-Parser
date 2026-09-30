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

Usage:
    python tools/warning_report.py                          # latest pipeline run
    python tools/warning_report.py /srv/dev/wrf/logs/2026-09-29_022234
    python tools/warning_report.py /srv/dev/wrf/dev/logs/latest.log --no-baseline
    python tools/warning_report.py --json > report.json

Exit code: 0 = no groups, 1 = at least one group, 2 = bad input.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path
from urllib.parse import quote

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


def default_export_dir(log: Path) -> Path | None:
    """exports/<version> named after the log (<version>.log), else the newest one."""
    stem = log.stem
    if re.match(r"^\d{4}-\d\d-\d\d(-\d+)?$", stem) and (EXPORTS_ROOT / stem).is_dir():
        return EXPORTS_ROOT / stem
    run_log = log.parent / "run.log"
    if run_log.is_file():
        m = re.search(r"version=(\d{4}-\d\d-\d\d(?:-\d+)?)", run_log.read_text(errors="replace"))
        if m and (EXPORTS_ROOT / m[1]).is_dir():
            return EXPORTS_ROOT / m[1]
    versions = sorted(p for p in EXPORTS_ROOT.glob("*") if p.is_dir())
    return versions[-1] if versions else None


# -------------------------------------------------------------------- output

def _clip(text: str, width: int) -> str:
    text = text.replace("|", "\\|").replace("\n", " ")
    return text if len(text) <= width else text[: width - 1] + "…"


def render_markdown(log: Path, baseline: Path | None, export_dir: Path | None, groups, total: int) -> str:
    ordered = sorted(groups.values(), key=lambda g: (KIND_ORDER[g["kind"]], -g["count"]))
    by_kind = {k: [g for g in ordered if g["kind"] == k] for k in KIND_ORDER}
    out = [f"# Parse warning report", "",
           f"- log: `{log}`",
           f"- baseline: `{baseline}`" if baseline else "- baseline: none (NEW markers unavailable)",
           f"- export dir: `{export_dir}`" if export_dir else "- export dir: none (files not resolved)",
           f"- {total} WARNING+ lines -> {len(groups)} groups: "
           + ", ".join(f"{len(by_kind[k])} {k}" for k in KIND_ORDER), ""]
    if not groups:
        out.append("Clean: no warnings or errors.")
        return "\n".join(out)

    n = 0
    for kind in KIND_ORDER:
        if not by_kind[kind]:
            continue
        out += [f"## {kind} ({len(by_kind[kind])})", ""]
        for g in by_kind[kind]:
            n += 1
            g["n"] = n
            new = " **NEW**" if g.get("new") else ""
            out.append(f"### {n}. {_clip(g['title'], 160)}{new}")
            out.append("")
            out.append(f"- count: {g['count']}")
            if kind == "unknown-property":
                if g.get("parser"):
                    out.append(f"- parser: `{g['parser']}`")
                if g["owners"]:
                    out.append(f"- owners: {', '.join(f'`{o}`' for o in g['owners'])}")
                out.append(f"- value: `{_clip(g['examples'][0], 240)}`")
            else:
                out.append(f"- logged at: `{g['logged_at']}` ({g['level']})")
                if g["ids"]:
                    out.append(f"- ids: {', '.join(f'`{i}`' for i in g['ids'])}")
                for ex in g["examples"]:
                    out.append(f"- example: `{_clip(ex, 240)}`")
                for d in g.get("detail", [])[:MAX_DETAIL_LINES]:
                    out.append(f"    {d}")
            for f in g["files"]:
                out.append(f"- export: `{f}`  [viewer]({VIEWER_URL}#{quote(f)})")
            out.append("")
    return "\n".join(out)


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
    args = ap.parse_args()

    log = resolve_log(args.log)
    groups = group_records(log, args.max_examples)
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
    else:
        print(render_markdown(log, baseline, export_dir if index else None, groups, total))
    return 1 if groups else 0


if __name__ == "__main__":
    raise SystemExit(main())
