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

# Interactive rc file for the user's login shell. zsh is the macOS default.
case "${SHELL:-}" in
  */zsh) SHELL_PROFILE="${ZDOTDIR:-$HOME}/.zshrc" ;;
  */bash) SHELL_PROFILE="$HOME/.bashrc" ;;
  *) SHELL_PROFILE="$HOME/.profile" ;;
esac

is_on_path() {
  case ":$PATH:" in
    *":$BIN_DIR:"*) return 0 ;;
    *":$LOCAL_BIN:"*) return 0 ;;
    *) return 1 ;;
  esac
}

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

sync_shell_env() {
  destination=$1
  if "$PYTHON" - "$MODE" "$destination" "$REPO_ROOT" <<'PY'
import pathlib
import re
import shlex
import sys

mode, destination_name, repo_root = sys.argv[1:]
destination = pathlib.Path(destination_name)
begin = "# BEGIN ai-knowledge-harness"
end = "# END ai-knowledge-harness"
block = "\n".join(
    [
        begin,
        f"export AI_KB_REPO={shlex.quote(repo_root)}",
        'export AI_KB_ROOT="$AI_KB_REPO"',
        'case ":$PATH:" in',
        '  *":$AI_KB_REPO/bin:"*) ;;',
        '  *) PATH="$AI_KB_REPO/bin:$PATH" ;;',
        "esac",
        "export PATH",
        end,
    ]
) + "\n"
existing = destination.read_text(encoding="utf-8") if destination.exists() else ""
pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"\r?\n?", re.S)
stripped = pattern.sub("", existing).rstrip()
desired = (stripped + "\n\n" if stripped else "") + block
has_block = begin in existing and end in existing

if mode == "check":
    raise SystemExit(0 if has_block and existing == desired else 1)
if mode == "uninstall":
    if not has_block:
        raise SystemExit(3)
    if stripped:
        destination.write_text(stripped + "\n", encoding="utf-8", newline="\n")
    else:
        destination.unlink()
    raise SystemExit(0)
if existing != desired:
    destination.parent.mkdir(parents=True, exist_ok=True)
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

printf '\n[0b] repository append-only hook\n'
hooks_path=$(git -C "$REPO_ROOT" config --local --get core.hooksPath 2>/dev/null || true)
if [ "$MODE" = uninstall ]; then
  if [ "$hooks_path" = .githooks ]; then
    git -C "$REPO_ROOT" config --local --unset core.hooksPath
    wrote 'removed local core.hooksPath'
  else
    skip "core.hooksPath (is '$hooks_path')"
  fi
elif [ "$MODE" = check ]; then
  if [ "$hooks_path" = .githooks ]; then
    ok 'core.hooksPath=.githooks'
  else
    missing "core.hooksPath (is '$hooks_path')"
  fi
else
  git -C "$REPO_ROOT" config --local core.hooksPath .githooks
  wrote 'core.hooksPath=.githooks'
fi

printf '\n[1] command, repository pointer, and shell environment\n'
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

sync_shell_env "$SHELL_PROFILE"
if [ "$MODE" != uninstall ] && ! is_on_path; then
  # The rc file is authoritative; a non-interactive shell has not sourced it
  # yet, so this is informational rather than drift.
  skip "$BIN_DIR not yet on PATH in this shell (open a new terminal)"
fi

printf '\n[2] VS Code global instructions\n'
vscode_source="$SURFACES/vscode/ai-knowledge-base.instructions.md"
vscode_found=0
for root in "$HOME/.config" "$HOME/Library/Application Support"; do
  for name in \
    "Code" \
    "Code - Insiders" \
    "Code - Exploration" \
    "VSCodium" \
    "Cursor" \
    "Windsurf"
  do
    if [ -d "$root/$name" ]; then
      vscode_found=$((vscode_found + 1))
      sync_file "$vscode_source" "$root/$name/User/prompts/ai-knowledge-base.instructions.md"
    fi
  done
done
if [ "$vscode_found" -eq 0 ]; then
  skip 'no supported VS Code profile found'
fi

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
  printf '%s\n' 'open a new terminal so the removed shell environment takes effect.'
else
  printf '%s\n' 'done - open a new terminal, then run: aikb check'
  if ! is_on_path; then
    printf 'this shell does not yet expose aikb; %s was updated.\n' "$SHELL_PROFILE"
    printf 'to use it immediately without a new terminal, run:\n'
    printf '  . %s\n' "$SHELL_PROFILE"
  fi
fi
