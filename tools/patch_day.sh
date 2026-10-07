#!/usr/bin/env bash
# Patch-day parser dev loop: re-parse a patch's export with
# the parser you are editing, into scratch dirs, and review what changed in the
# parsed output as a git diff (VS Code Source Control).
#
# It never pushes data. The full human process
# is in WRFrontiersDB-Orchestrator/PATCH_DAY.md; the agent process is the
# patch-warnings skill (.claude/skills/patch-warnings/SKILL.md).
#
#   tools/patch_day.sh resolve [version]  print "<version> <run-dir>": the newest
#                                         completed pipeline run (of <version>, if
#                                         given); fails listing the versions on disk
#   tools/patch_day.sh init <version>     point the loop at a patch: write .env,
#                                         reset the review repo to the pipeline's
#                                         parsed output for <version> (baseline)
#   tools/patch_day.sh parse              scratch-parse, sync into the review
#                                         repo, write the warning report
#   tools/patch_day.sh report [args]      grouped warning report of the latest
#                                         scratch parse -> reports/latest.md
#                                         (tools/warning_report.py; --stdout to print)
#   tools/patch_day.sh sync               re-copy scratch output into review repo
#   tools/patch_day.sh checkpoint <msg>   accept a decision step: commit the parser
#                                         code (src/, tests/) on patch/<version> and
#                                         the review repo, same message, linked by
#                                         hash + the decision ids now done
#   tools/patch_day.sh status             version, checkpoints, diff vs baseline
#   tools/patch_day.sh viewer [args]      asset viewer on the patch's export
#
# Layout (all under $WRF_ROOT/dev):
#   VERSION        the patch version the loop is pointed at
#   parsed/        scratch OUTPUT_DIR (cleared by every parse)
#   textures/      scratch TEXTURE_OUTPUT_DIR
#   logs/          one log per scratch parse; latest.log -> newest
#   parsed-review/ git repo: baseline commit = pipeline output, working tree =
#                  latest scratch parse. Add it to your VS Code workspace.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRF_ROOT="${WRF_ROOT:-/srv/dev/wrf}"
DEV_DIR="$WRF_ROOT/dev"
SCRATCH_OUT="$DEV_DIR/parsed"
SCRATCH_TEX="$DEV_DIR/textures"
LOG_DIR="$DEV_DIR/logs"
REVIEW_DIR="$DEV_DIR/parsed-review"
VERSION_FILE="$DEV_DIR/VERSION"
PY="$REPO_DIR/.venv/bin/python"

die() { echo "patch_day: $*" >&2; exit 1; }

require_venv() {
  [[ -x "$PY" ]] || die "no venv at $REPO_DIR/.venv (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)"
}

version() {
  [[ -f "$VERSION_FILE" ]] || die "not initialised - run: tools/patch_day.sh init <version>"
  cat "$VERSION_FILE"
}

# Set KEY="value" in the repo's .env (created from .env.example if missing).
set_env() {
  local env_file="$REPO_DIR/.env" key="$1" value="$2"
  [[ -f "$env_file" ]] || cp "$REPO_DIR/.env.example" "$env_file"
  if grep -q "^${key}=" "$env_file"; then
    sed -i "s|^${key}=.*|${key}=\"${value}\"|" "$env_file"
  else
    printf '%s="%s"\n' "$key" "$value" >> "$env_file"
  fi
}

# Newest completed pipeline run dir (of version $1, if given), as "<version> <run-dir>".
latest_run() {
  local want="${1:-}" d v
  for d in $(ls -1r "$WRF_ROOT/logs"); do
    [[ -f "$WRF_ROOT/logs/$d/run.log" ]] || continue
    grep -q 'Pipeline complete' "$WRF_ROOT/logs/$d/run.log" || continue
    v="$(grep -om1 'version=[^ ]*' "$WRF_ROOT/logs/$d/run.log" | cut -d= -f2)" || continue
    [[ -z "$want" || "$v" == "$want" ]] && { echo "$v $d"; return 0; }
  done
  return 1
}

cmd_resolve() {
  local v="${1:-}" found
  if [[ -n "$v" && ! -d "$WRF_ROOT/data/exports/$v" ]]; then
    found="$(latest_run)" || found="none"
    die "no export for '$v'. On disk: $(ls "$WRF_ROOT/data/exports" | tr '\n' ' ')- latest completed run: $found"
  fi
  latest_run "$v" || die "no completed pipeline run${v:+ for $v} under $WRF_ROOT/logs"
}

cmd_init() {
  local v="${1:-}"
  [[ "$v" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}(-[0-9]+)?$ ]] || die "usage: init <yyyy-mm-dd[-N]>"
  require_venv
  local exports="$WRF_ROOT/data/exports/$v" pipeline_parsed="$WRF_ROOT/data/parsed/$v"
  [[ -d "$exports" ]] || die "no export for $v at $exports"
  [[ -d "$pipeline_parsed" ]] || die "no pipeline parse for $v at $pipeline_parsed"

  mkdir -p "$DEV_DIR" "$SCRATCH_OUT" "$SCRATCH_TEX" "$LOG_DIR"
  echo "$v" > "$VERSION_FILE"

  # .env: makes a plain `python src/run.py` and the asset viewer target this
  # patch, and pins push OFF (the all-SHOULD_-false -> all-true rule would
  # otherwise turn it on).
  set_env SHOULD_PARSE True
  set_env SHOULD_PUSH_DATA False
  set_env EXPORT_DIR "$exports"
  set_env OUTPUT_DIR "$SCRATCH_OUT"
  set_env TEXTURE_OUTPUT_DIR "$SCRATCH_TEX"
  set_env GAME_VERSION "$v"

  rm -rf "$REVIEW_DIR"
  mkdir -p "$REVIEW_DIR"
  git -C "$REVIEW_DIR" init -q -b main
  rsync -a "$pipeline_parsed/" "$REVIEW_DIR/"
  git -C "$REVIEW_DIR" add -A
  git -C "$REVIEW_DIR" commit -q -m "baseline: pipeline parse of $v"
  git -C "$REVIEW_DIR" tag baseline

  echo "patch_day: pointed at $v"
  echo "  export   : $exports"
  echo "  baseline : $pipeline_parsed -> $REVIEW_DIR (tag 'baseline')"
  echo "  .env     : $REPO_DIR/.env (push off)"
  echo "next: tools/patch_day.sh parse"
}

cmd_sync() {
  [[ -d "$REVIEW_DIR/.git" ]] || die "no review repo - run init first"
  rsync -a --delete --exclude .git "$SCRATCH_OUT/" "$REVIEW_DIR/"
  local changed
  changed="$(git -C "$REVIEW_DIR" status --porcelain | wc -l)"
  echo "patch_day: review repo synced - $changed file(s) differ from the last checkpoint"
  git -C "$REVIEW_DIR" diff --shortstat
}

cmd_parse() {
  require_venv
  local v stamp log rc
  v="$(version)"
  stamp="$(date +%Y%m%d_%H%M%S)"
  log="$LOG_DIR/parse-$v-$stamp.log"
  mkdir -p "$LOG_DIR"
  echo "patch_day: scratch parse of $v -> $SCRATCH_OUT (log: $log)"
  set +e
  (cd "$REPO_DIR" && PYTHONUNBUFFERED=1 "$PY" src/run.py \
      --log-level DEBUG \
      --should-parse true \
      --should-push-data false \
      --game-name WRFrontiers \
      --export-dir "$WRF_ROOT/data/exports/$v" \
      --output-dir "$SCRATCH_OUT" \
      --texture-output-dir "$SCRATCH_TEX") > "$log" 2>&1
  rc=$?
  set -e
  ln -sfn "$(basename "$log")" "$LOG_DIR/latest.log"
  if [[ $rc -ne 0 ]]; then
    echo "patch_day: PARSE FAILED (exit $rc) - review repo NOT synced. Last lines:" >&2
    tail -n 25 "$log" >&2
    exit $rc
  fi
  cmd_sync
  cmd_report
}

cmd_report() {
  local latest="$LOG_DIR/latest.log"
  [[ -e "$latest" ]] || die "no scratch parse yet - run: tools/patch_day.sh parse"
  local rc=0
  "$PY" "$REPO_DIR/tools/warning_report.py" "$(readlink -f "$latest")" \
      --export-dir "$WRF_ROOT/data/exports/$(version)" "$@" || rc=$?
  # 1 just means "there are groups"; only surface real failures.
  [[ $rc -le 1 ]] || exit $rc
}

# Decisions this checkpoint covers: `done` entries of decisions/<version>.json not
# yet tied to a checkpoint. `pending` prints their ids; `mark <review> <code>`
# records the checkpoint (and code commit, if any) on them.
checkpoint_decisions() {
  local file="$REPO_DIR/decisions/$(version).json"
  [[ -f "$file" ]] || return 0
  "$PY" - "$file" "$@" <<'PY'
import json, sys
path, mode, *args = sys.argv[1:]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
pending = [gid for gid, e in data.get("groups", {}).items()
           if e.get("status") == "done" and not e.get("checkpoint")]
if mode == "pending":
    print(" ".join(pending))
else:
    review, code = args
    for gid in pending:
        data["groups"][gid]["checkpoint"] = review
        data["groups"][gid]["commit"] = code
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    import os
    os.replace(path + ".tmp", path)
PY
}

# One checkpoint = one decision step on both sides: the parser code change
# (src/, tests/) is committed on patch/<version>, and the review repo's parsed
# output is committed with the same message plus the code commit's hash. Either
# side may be empty (a sanity parse has no code; a skip-only change no data diff).
cmd_checkpoint() {
  [[ $# -ge 1 ]] || die "usage: checkpoint <message>"
  [[ -d "$REVIEW_DIR/.git" ]] || die "no review repo - run init first"
  require_venv
  local msg="$*" v branch code_files data_changed=0 log stale="" f ids code_sha="" review_sha
  v="$(version)"
  branch="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)"
  code_files="$(git -C "$REPO_DIR" status --porcelain --untracked-files=all -- src tests | cut -c4-)"
  git -C "$REVIEW_DIR" add -A
  git -C "$REVIEW_DIR" diff --cached --quiet || data_changed=1
  if [[ -z "$code_files" && $data_changed -eq 0 ]]; then
    echo "patch_day: nothing to checkpoint"
    return
  fi

  if [[ -n "$code_files" ]]; then
    [[ "$branch" == "patch/$v" ]] \
      || die "parser code changes on '$branch' - checkpoints commit code only on patch/$v (git switch -c patch/$v)"
    # The data side must come from this code: refuse if it was edited after the last parse.
    log="$(readlink -f "$LOG_DIR/latest.log" 2>/dev/null || true)"
    [[ -n "$log" ]] || die "no scratch parse yet - run: tools/patch_day.sh parse"
    while IFS= read -r f; do
      [[ -e "$REPO_DIR/$f" && "$REPO_DIR/$f" -nt "$log" ]] && stale+=" $f"
    done <<< "$code_files"
    [[ -z "$stale" ]] || die "changed since the last scratch parse:$stale - run: tools/patch_day.sh parse"
  fi

  ids="$(checkpoint_decisions pending)"
  if [[ -n "$code_files" ]]; then
    git -C "$REPO_DIR" add -A -- src tests
    git -C "$REPO_DIR" commit -q -m "$msg" ${ids:+-m "Decisions: $ids"} -- src tests
    code_sha="$(git -C "$REPO_DIR" rev-parse --short HEAD)"
  fi
  git -C "$REVIEW_DIR" commit -q --allow-empty -m "$msg" \
      ${code_sha:+-m "Code: $code_sha ($branch)"} ${ids:+-m "Decisions: $ids"}
  review_sha="$(git -C "$REVIEW_DIR" rev-parse --short HEAD)"
  [[ -z "$ids" ]] || checkpoint_decisions mark "$review_sha" "$code_sha"

  echo "patch_day: checkpoint '$msg'"
  echo "  review repo : $review_sha$([[ $data_changed -eq 1 ]] || echo ' (no data change)')"
  echo "  code        : ${code_sha:-none} ${code_sha:+on $branch}"
  echo "  decisions   : ${ids:-none}"
}

cmd_status() {
  local v
  v="$(version)"
  echo "version  : $v"
  echo "repo     : $REPO_DIR ($(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD))"
  if [[ -d "$REVIEW_DIR/.git" ]]; then
    echo "checkpoints:"
    git -C "$REVIEW_DIR" log --oneline | sed 's/^/  /'
    echo "uncommitted vs last checkpoint: $(git -C "$REVIEW_DIR" status --porcelain | wc -l) file(s)"
    git -C "$REVIEW_DIR" add -A -N . >/dev/null 2>&1 || true
    echo "total vs baseline:"
    git -C "$REVIEW_DIR" diff --stat baseline | tail -n 1 | sed 's/^/  /'
  fi
  [[ -e "$LOG_DIR/latest.log" ]] && echo "latest log: $(readlink -f "$LOG_DIR/latest.log")"
  return 0
}

cmd_viewer() {
  "$PY" "$REPO_DIR/tools/asset-viewer/serve.py" --export-dir "$WRF_ROOT/data/exports/$(version)" "$@"
}

sub="${1:-}"
shift || true
case "$sub" in
  resolve)    cmd_resolve "$@" ;;
  init)       cmd_init "$@" ;;
  parse)      cmd_parse ;;
  report)     cmd_report "$@" ;;
  sync)       cmd_sync ;;
  checkpoint) cmd_checkpoint "$@" ;;
  status)     cmd_status ;;
  viewer)     cmd_viewer "$@" ;;
  *) sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
