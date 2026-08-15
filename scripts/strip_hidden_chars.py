#!/usr/bin/env python3
"""Remove hidden and smuggled Unicode characters from generated text.

Model output routinely carries characters that survive copy-paste but are
invisible in review: zero-width spaces, bidirectional controls, and Unicode
tag characters. Some are cosmetic noise. Others are a documented attack
surface, because a reviewer and a compiler can be shown different source.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Iterator, Sequence

# Never legitimate in prose or source, and invisible to a reviewer.
INVISIBLE = frozenset(
    "\u200b"  # zero width space
    "\u2060"  # word joiner
    "\ufeff"  # zero width no-break space / byte order mark
    "\u00ad"  # soft hyphen
    "\u180e"  # mongolian vowel separator
    "\u115f"  # hangul choseong filler
    "\u1160"  # hangul jungseong filler
    "\u3164"  # hangul filler
    "\uffa0"  # halfwidth hangul filler
    "\u2061\u2062\u2063\u2064"  # invisible math operators
)

# Reordering controls. These enable Trojan Source style attacks, where the
# rendered order of a line differs from the order a compiler consumes.
BIDI = frozenset(
    "\u200e\u200f"  # left-to-right / right-to-left mark
    "\u061c"  # arabic letter mark
    "\u202a\u202b\u202c\u202d\u202e"  # embedding, override, pop
    "\u2066\u2067\u2068\u2069"  # isolates
)

# Joiners and variation selectors are load-bearing in emoji, Indic, Arabic,
# and Persian text, so they are only removed when explicitly requested.
JOINERS = frozenset(
    "\u200c\u200d" + "".join(chr(cp) for cp in range(0xFE00, 0xFE10))
) | frozenset(chr(cp) for cp in range(0xE0100, 0xE01F0))

WHITESPACE_TO_SPACE = frozenset(
    "\u00a0"  # no-break space
    "\u1680"  # ogham space mark
    "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
    "\u202f"  # narrow no-break space
    "\u205f"  # medium mathematical space
    "\u3000"  # ideographic space
)

LINE_SEPARATORS = frozenset("\u2028\u2029")

TYPOGRAPHY = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
    "\u2032": "'", "\u2033": '"',
    "\u2010": "-", "\u2011": "-", "\u2012": "-",
    "\u2013": "-", "\u2014": "-", "\u2015": "-",
    "\u2026": "...",
    "\u00b4": "'",
}

TAG_START, TAG_END = 0xE0020, 0xE007E
TAG_TERMINATOR = 0xE007F
WAVING_BLACK_FLAG = "\U0001f3f4"

DEFAULT_EXTENSIONS = frozenset(
    """.bat .c .cfg .cpp .cs .css .csv .go .h .htm .html .ini .java .js .json
    .jsx .kt .less .md .mdx .php .ps1 .py .rb .rs .rst .scss .sh .sql .svg
    .swift .toml .ts .tsx .txt .vue .xml .yaml .yml""".split()
)

EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git", ".hg", ".svn", ".mypy_cache", ".pytest_cache", ".ruff_cache",
        ".venv", "venv", "__pycache__", "node_modules", "build", "dist",
        ".tox", ".idea", ".vscode-test",
    }
)

CLASS_LABELS = ("invisible", "bidi", "tag", "joiner", "whitespace", "typography")


class SanitizeError(RuntimeError):
    """A characterized sanitizer failure."""


def _protected_tag_spans(text: str) -> set[int]:
    """Indices belonging to valid emoji tag sequences, such as subdivision flags.

    A bare tag character is a smuggling vector, but the same code points spell
    out the England, Scotland, and Wales flags when they follow U+1F3F4 and end
    with the cancel-tag terminator. Those runs are preserved.
    """
    protected: set[int] = set()
    index = text.find(WAVING_BLACK_FLAG)
    while index != -1:
        cursor = index + 1
        while cursor < len(text) and TAG_START <= ord(text[cursor]) <= TAG_END:
            cursor += 1
        if (
            cursor > index + 1
            and cursor < len(text)
            and ord(text[cursor]) == TAG_TERMINATOR
        ):
            protected.update(range(index, cursor + 1))
            index = text.find(WAVING_BLACK_FLAG, cursor + 1)
        else:
            index = text.find(WAVING_BLACK_FLAG, index + 1)
    return protected


def sanitize_text(
    text: str,
    *,
    keep_bidi: bool = False,
    strip_joiners: bool = False,
    normalize_whitespace: bool = True,
    typography: bool = False,
) -> tuple[str, dict[str, int]]:
    """Return sanitized text and a per-class count of what was changed."""
    counts = {label: 0 for label in CLASS_LABELS}
    protected = _protected_tag_spans(text)
    out: list[str] = []

    for position, char in enumerate(text):
        code_point = ord(char)

        if char in INVISIBLE:
            counts["invisible"] += 1
            continue
        if not keep_bidi and char in BIDI:
            counts["bidi"] += 1
            continue
        if TAG_START <= code_point <= TAG_TERMINATOR and position not in protected:
            counts["tag"] += 1
            continue
        if strip_joiners and char in JOINERS:
            counts["joiner"] += 1
            continue
        if normalize_whitespace and char in WHITESPACE_TO_SPACE:
            counts["whitespace"] += 1
            out.append(" ")
            continue
        if normalize_whitespace and char in LINE_SEPARATORS:
            counts["whitespace"] += 1
            out.append("\n")
            continue
        if typography and char in TYPOGRAPHY:
            counts["typography"] += 1
            out.append(TYPOGRAPHY[char])
            continue

        out.append(char)

    return "".join(out), counts


def _describe(counts: dict[str, int]) -> str:
    found = [f"{label}={count}" for label, count in counts.items() if count]
    return ", ".join(found) if found else "clean"


def _total(counts: dict[str, int]) -> int:
    return sum(counts.values())


def iter_files(paths: Sequence[Path], extensions: frozenset[str]) -> Iterator[Path]:
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            yield path
            continue
        if not path.is_dir():
            raise SanitizeError(f"path does not exist: {path}")
        for child in sorted(path.rglob("*")):
            if not child.is_file():
                continue
            if any(part in EXCLUDED_DIRECTORIES for part in child.parts):
                continue
            if extensions and child.suffix.lower() not in extensions:
                continue
            yield child


def _read(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return handle.read()
    except (UnicodeDecodeError, OSError):
        return None


def _write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _options(args: argparse.Namespace) -> dict[str, bool]:
    return {
        "keep_bidi": args.keep_bidi,
        "strip_joiners": args.strip_joiners,
        "normalize_whitespace": not args.no_whitespace,
        "typography": args.typography,
    }


def _run_stdin(args: argparse.Namespace) -> int:
    text = sys.stdin.read()
    cleaned, counts = sanitize_text(text, **_options(args))
    sys.stdout.write(cleaned)
    if not args.quiet and _total(counts):
        print(f"stdin: {_describe(counts)}", file=sys.stderr)
    return 0


def _run_paths(args: argparse.Namespace, extensions: frozenset[str]) -> int:
    affected = 0
    skipped = 0
    for path in iter_files(args.paths, extensions):
        text = _read(path)
        if text is None:
            skipped += 1
            continue
        cleaned, counts = sanitize_text(text, **_options(args))
        if not _total(counts):
            continue
        affected += 1
        if args.write:
            _write(path, cleaned)
            if not args.quiet:
                print(f"cleaned {path}: {_describe(counts)}")
        elif not args.quiet:
            print(f"FOUND   {path}: {_describe(counts)}", file=sys.stderr)

    if args.write:
        if not args.quiet:
            print(f"OK    {affected} file(s) cleaned, {skipped} skipped")
        return 0
    if affected:
        if not args.quiet:
            print(f"\n{affected} file(s) contain hidden characters", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"OK    no hidden characters found, {skipped} skipped")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="strip_hidden_chars",
        description="Remove hidden and smuggled Unicode characters from text",
    )
    parser.add_argument("paths", nargs="*", type=Path, help="files or directories")
    parser.add_argument("--stdin", action="store_true", help="clean stdin to stdout")
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite files in place (default: report only, non-zero when found)",
    )
    parser.add_argument("--keep-bidi", action="store_true", help="preserve bidi controls")
    parser.add_argument(
        "--strip-joiners",
        action="store_true",
        help="also remove ZWJ, ZWNJ, and variation selectors (breaks some emoji)",
    )
    parser.add_argument(
        "--no-whitespace",
        action="store_true",
        help="do not fold exotic spaces to ASCII space",
    )
    parser.add_argument(
        "--typography",
        action="store_true",
        help="also fold curly quotes, dashes, and ellipsis to ASCII",
    )
    parser.add_argument("--ext", action="append", help="limit to this extension")
    parser.add_argument("--all-extensions", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.stdin and args.paths:
        parser.error("--stdin does not take paths")
    if not args.stdin and not args.paths:
        parser.error("provide at least one path, or --stdin")

    extensions: frozenset[str] = frozenset()
    if not args.all_extensions:
        chosen: Iterable[str] = args.ext or DEFAULT_EXTENSIONS
        extensions = frozenset(
            item if item.startswith(".") else f".{item}" for item in chosen
        )

    try:
        if args.stdin:
            return _run_stdin(args)
        return _run_paths(args, extensions)
    except SanitizeError as exc:
        print(f"ABSTENTION  {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
