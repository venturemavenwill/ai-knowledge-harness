#!/usr/bin/env sh
set -eu

MODE=install
SKIP_FUTURE=0
for arg in "$@"; do
  case "$arg" in
    --check) MODE=check ;;
    --uninstall) MODE=uninstall ;;
    --skip-future-tools) SKIP_FUTURE=1 ;;
    *)
      printf 'unknown argument: %s\n' "$arg" >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
BIN_DIR="$REPO_ROOT/bin"
SURFACES="$REPO_ROOT/surfaces"
LOCAL_BIN="${XDG_BIN_HOME:-$HOME/.local/bin}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/ai-knowledge-harness"
DRIFT=0

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  printf '%s\n' 'Python 3.9 or newer is required.' >&2
  exit 2
fi

"$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' ||
  { printf '%s\n' 'Python 3.9 or newer is required.' >&2; exit 2; }

ok() { printf '  ok      %s\n' "$1"; }
wrote() { printf '  wrote   %s\n' "$1"; }
missing() { printf '  MISSING %s\n' "$1" >&2; DRIFT=$((DRIFT + 1)); }
stale() { printf '  STALE   %s\n' "$1" >&2; DRIFT=$((DRIFT + 1)); }
skip() { printf '  skip    %s\n' "$1"; }

sync_file() {
  source=$1
  destination=$2
  if [ "$MODE" = uninstall ]; then
    if [ ! -f "$destination" ]; then
      skip "$destination (absent)"
    elif cmp -s "$source" "$destination"; then
      rm -f -- "$destination"
      wrote "removed $destination"
    else
      stale "$destination (user-modified; preserved)"
    fi
    return
  fi
  if [ "$MODE" = check ]; then
    if [ ! -f "$destination" ]; then
      missing "$destination"
    elif ! cmp -s "$source" "$destination"; then
      stale "$destination"
    else
      ok "$destination"
    fi
    return
  fi
  if [ -f "$destination" ] && cmp -s "$source" "$destination"; then
    ok "$destination"
    return
  fi
  mkdir -p -- "$(dirname -- "$destination")"
  if [ -f "$destination" ] && [ ! -f "$destination.aikb-bak" ]; then
    cp -- "$destination" "$destination.aikb-bak"
  fi
  cp -- "$source" "$destination"
  wrote "$destination"
}

sync_block() {
  block_file=$1
  destination=$2
  create_dir=$3
  directory=$(dirname -- "$destination")
  if [ ! -d "$directory" ]; then
    if [ "$MODE" != install ] || [ "$create_dir" -ne 1 ]; then
      skip "$destination (directory absent)"
      return
    fi
    mkdir -p -- "$directory"
  fi
  if "$PYTHON" - "$MODE" "$block_file" "$destination" <<'PY'
import pathlib
import re
import sys

mode, block_name, destination_name = sys.argv[1:]
block_path = pathlib.Path(block_name)
destination = pathlib.Path(destination_name)
begin = "<!-- BEGIN ai-knowledge-harness -->"
end = "<!-- END ai-knowledge-harness -->"
legacy_begin = "<!-- BEGIN ai-knowledge-base"
legacy_end = "<!-- END ai-knowledge-base -->"
existing = destination.read_text(encoding="utf-8") if destination.exists() else ""
block = block_path.read_text(encoding="utf-8").rstrip() + "\n"
patterns = (
    re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"\r?\n?", re.S),
    re.compile(re.escape(legacy_begin) + r".*?" + re.escape(legacy_end) + r"\r?\n?", re.S),
)
stripped = existing
for pattern in patterns:
    stripped = pattern.sub("", stripped)
stripped = stripped.rstrip()
desired = (stripped + "\n\n" if stripped else "") + block
has_new = begin in existing and end in existing

if mode == "check":
    raise SystemExit(0 if has_new and existing == desired else 1)
if mode == "uninstall":
    if not has_new:
        raise SystemExit(3)
    if stripped:
        destination.write_text(stripped + "\n", encoding="utf-8", newline="\n")
    else:
        destination.unlink()
    raise SystemExit(0)
if existing != desired:
    destination.write_text(desired, encoding="utf-8", newline="\n")
    raise SystemExit(4)
raise SystemExit(0)
PY
  then
    result=0
  else
    result=$?
  fi
  case "$result" in
    0) ok "$destination" ;;
    1) stale "$destination" ;;
    3) skip "$destination (managed block absent)" ;;
    4) wrote "$destination" ;;
    *) return "$result" ;;
  esac
}

printf '\nAI knowledge harness - repository: %s\n' "$REPO_ROOT"
printf 'mode: %s\n' "$MODE"

if [ "$MODE" != uninstall ]; then
  printf '\n[0] repository validation\n'
  "$PYTHON" "$BIN_DIR/aikb.py" --repo "$REPO_ROOT" validate --projection
fi

printf '\n[1] command and repository pointer\n'
if [ "$MODE" = uninstall ]; then
  if [ -L "$LOCAL_BIN/aikb" ] && [ "$(readlink "$LOCAL_BIN/aikb")" = "$BIN_DIR/aikb" ]; then
    rm -f -- "$LOCAL_BIN/aikb"
    wrote "removed $LOCAL_BIN/aikb"
  else
    skip "$LOCAL_BIN/aikb (not managed by this checkout)"
  fi
  if [ -f "$CONFIG_DIR/repo" ] && [ "$(cat "$CONFIG_DIR/repo")" = "$REPO_ROOT" ]; then
    rm -f -- "$CONFIG_DIR/repo"
    wrote "removed $CONFIG_DIR/repo"
  fi
elif [ "$MODE" = check ]; then
  if [ -L "$LOCAL_BIN/aikb" ] && [ "$(readlink "$LOCAL_BIN/aikb")" = "$BIN_DIR/aikb" ]; then
    ok "$LOCAL_BIN/aikb"
  else
    missing "$LOCAL_BIN/aikb"
  fi
  if [ -f "$CONFIG_DIR/repo" ] && [ "$(cat "$CONFIG_DIR/repo")" = "$REPO_ROOT" ]; then
    ok "$CONFIG_DIR/repo"
  else
    missing "$CONFIG_DIR/repo"
  fi
else
  mkdir -p -- "$LOCAL_BIN" "$CONFIG_DIR"
  chmod +x "$BIN_DIR/aikb" "$BIN_DIR/aikb.py"
  ln -sfn -- "$BIN_DIR/aikb" "$LOCAL_BIN/aikb"
  printf '%s' "$REPO_ROOT" > "$CONFIG_DIR/repo"
  wrote "$LOCAL_BIN/aikb"
  wrote "$CONFIG_DIR/repo"
fi

printf '\n[2] VS Code global instructions\n'
vscode_source="$SURFACES/vscode/ai-knowledge-base.instructions.md"
for profile in \
  "$HOME/.config/Code" \
  "$HOME/.config/Code - Insiders" \
  "$HOME/Library/Application Support/Code" \
  "$HOME/Library/Application Support/Code - Insiders"
do
  if [ -d "$profile" ]; then
    sync_file "$vscode_source" "$profile/User/prompts/ai-knowledge-base.instructions.md"
  fi
done

printf '\n[3] user-level skills\n'
skill_source="$SURFACES/skill/SKILL.md"
sync_file "$skill_source" "$HOME/.copilot/skills/ai-knowledge-base/SKILL.md"
sync_file "$skill_source" "$HOME/.agents/skills/ai-knowledge-base/SKILL.md"

printf '\n[4] AGENTS.md-compatible managed blocks\n'
block_source="$SURFACES/agents/AGENTS-block.md"
sync_block "$block_source" "$HOME/AGENTS.md" 1
sync_block "$block_source" "$HOME/.codex/AGENTS.md" "$((1 - SKIP_FUTURE))"
sync_block "$block_source" "$HOME/.claude/CLAUDE.md" "$((1 - SKIP_FUTURE))"
sync_block "$block_source" "$HOME/.gemini/GEMINI.md" "$((1 - SKIP_FUTURE))"

printf '\n'
if [ "$MODE" = check ]; then
  if [ "$DRIFT" -eq 0 ]; then
    printf '%s\n' 'in sync - repository and installed surfaces are current.'
    exit 0
  fi
  printf '%s surface(s) missing or stale.\n' "$DRIFT" >&2
  exit 1
fi
if [ "$MODE" = uninstall ]; then
  printf '%s\n' 'done - managed knowledge surfaces were removed.'
else
  printf '%s\n' 'done - ensure ~/.local/bin is on PATH, then run: aikb check'
fi
