#!/usr/bin/env bash
# Patch-day parser dev loop on the home-server: re-parse a patch's export with
# the parser you are editing, into scratch dirs, and review what changed in the
# parsed output as a git diff (VS Code Source Control).
#
# Run it from the parser DEV WORKTREE (/srv/dev/repos/WRFrontiersDB-Parser-dev),
# never from the pipeline's clone. It never pushes data. The full human process
# is in WRFrontiersDB-Orchestrator/PATCH_DAY.md; the agent process is the
# patch-warnings skill (.claude/skills/patch-warnings/SKILL.md).
#
#   tools/patch_day.sh init <version>     point the loop at a patch: write .env,
#                                         reset the review repo to the pipeline's
#                                         parsed output for <version> (baseline)
#   tools/patch_day.sh parse              scratch-parse, sync into the review
#                                         repo, write the warning report
#   tools/patch_day.sh report [args]      grouped warning report of the latest
#                                         scratch parse -> reports/latest.md
#                                         (tools/warning_report.py; --stdout to print)
#   tools/patch_day.sh sync               re-copy scratch output into review repo
#   tools/patch_day.sh checkpoint <msg>   commit the review repo's current state
#   tools/patch_day.sh status             version, checkpoints, diff vs baseline
#   tools/patch_day.sh viewer [args]      asset viewer on the patch's export
#
# Layout (all under $WRF_ROOT/dev, default /srv/dev/wrf/dev):
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

require_dev_worktree() {
  local branch
  branch="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)"
  [[ "$branch" != "main" ]] \
    || die "on 'main' in $REPO_DIR - this looks like the pipeline's clone. Run from the dev worktree on a patch branch."
  [[ -x "$PY" ]] || die "no venv at $REPO_DIR/.venv (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)"
}

version() {
  [[ -f "$VERSION_FILE" ]] || die "not initialised - run: tools/patch_day.sh init <version>"
  cat "$VERSION_FILE"
}

# Set KEY="value" in the worktree's .env (created from .env.example if missing).
set_env() {
  local env_file="$REPO_DIR/.env" key="$1" value="$2"
  [[ -f "$env_file" ]] || cp "$REPO_DIR/.env.example" "$env_file"
  if grep -q "^${key}=" "$env_file"; then
    sed -i "s|^${key}=.*|${key}=\"${value}\"|" "$env_file"
  else
    printf '%s="%s"\n' "$key" "$value" >> "$env_file"
  fi
}

cmd_init() {
  local v="${1:-}"
  [[ "$v" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}(-[0-9]+)?$ ]] || die "usage: init <yyyy-mm-dd[-N]>"
  require_dev_worktree
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
  require_dev_worktree
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

cmd_checkpoint() {
  [[ $# -ge 1 ]] || die "usage: checkpoint <message>"
  [[ -d "$REVIEW_DIR/.git" ]] || die "no review repo - run init first"
  git -C "$REVIEW_DIR" add -A
  if git -C "$REVIEW_DIR" diff --cached --quiet; then
    echo "patch_day: nothing to checkpoint"
    return
  fi
  git -C "$REVIEW_DIR" commit -q -m "$*"
  echo "patch_day: checkpoint '$*'"
}

cmd_status() {
  local v
  v="$(version)"
  echo "version  : $v"
  echo "worktree : $REPO_DIR ($(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD))"
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
  init)       cmd_init "$@" ;;
  parse)      cmd_parse ;;
  report)     cmd_report "$@" ;;
  sync)       cmd_sync ;;
  checkpoint) cmd_checkpoint "$@" ;;
  status)     cmd_status ;;
  viewer)     cmd_viewer "$@" ;;
  *) sed -n '2,29p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
