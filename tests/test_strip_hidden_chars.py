from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SANITIZER = REPO / "scripts" / "strip_hidden_chars.py"
AIKB = REPO / "bin" / "aikb.py"

ZWSP = "\u200b"
SOFT_HYPHEN = "\u00ad"
NBSP = "\u00a0"
BOM = "\ufeff"
RLO = "\u202e"
POP_DIRECTIONAL = "\u202c"
ZWJ = "\u200d"
ZWNJ = "\u200c"
VARIATION_SELECTOR_16 = "\ufe0f"
LINE_SEPARATOR = "\u2028"
IDEOGRAPHIC_SPACE = "\u3000"

FAMILY = f"\U0001f468{ZWJ}\U0001f469{ZWJ}\U0001f467"
SCOTLAND_FLAG = (
    "\U0001f3f4\U000e0067\U000e0062\U000e0073\U000e0063\U000e0074\U000e007f"
)
SMUGGLED_TAGS = "\U000e0041\U000e0042"


def _load_module():
    spec = importlib.util.spec_from_file_location("strip_hidden_chars", SANITIZER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sanitizer = _load_module()


def clean(text: str, **options: bool) -> str:
    return sanitizer.sanitize_text(text, **options)[0]


def counts(text: str, **options: bool) -> dict[str, int]:
    return sanitizer.sanitize_text(text, **options)[1]


class SanitizeTextTests(unittest.TestCase):
    def test_invisible_characters_are_removed(self) -> None:
        self.assertEqual(clean(f"a{ZWSP}b{SOFT_HYPHEN}c{BOM}d"), "abcd")
        self.assertEqual(counts(f"a{ZWSP}b")["invisible"], 1)

    def test_bidirectional_controls_are_removed(self) -> None:
        self.assertEqual(clean(f"safe{RLO}evil{POP_DIRECTIONAL}"), "safeevil")
        self.assertEqual(counts(f"{RLO}x")["bidi"], 1)

    def test_bidirectional_controls_can_be_preserved(self) -> None:
        self.assertEqual(clean(f"a{RLO}b", keep_bidi=True), f"a{RLO}b")

    def test_smuggled_tag_characters_are_removed(self) -> None:
        self.assertEqual(clean(f"visible{SMUGGLED_TAGS}"), "visible")
        self.assertEqual(counts(SMUGGLED_TAGS)["tag"], 2)

    def test_valid_emoji_tag_sequence_is_preserved(self) -> None:
        self.assertEqual(clean(f"flag {SCOTLAND_FLAG}"), f"flag {SCOTLAND_FLAG}")
        self.assertEqual(counts(SCOTLAND_FLAG)["tag"], 0)

    def test_smuggled_tags_removed_while_flag_survives(self) -> None:
        text = f"{SCOTLAND_FLAG}{SMUGGLED_TAGS}"
        self.assertEqual(clean(text), SCOTLAND_FLAG)

    def test_unterminated_tag_run_after_flag_is_not_protected(self) -> None:
        text = "\U0001f3f4\U000e0067"
        self.assertEqual(clean(text), "\U0001f3f4")

    def test_joiners_are_preserved_by_default(self) -> None:
        text = f"{FAMILY} and {ZWNJ} and {VARIATION_SELECTOR_16}"
        self.assertEqual(clean(text), text)
        self.assertEqual(counts(text)["joiner"], 0)

    def test_joiners_are_removed_only_on_request(self) -> None:
        self.assertEqual(clean(FAMILY, strip_joiners=True), "\U0001f468\U0001f469\U0001f467")

    def test_exotic_whitespace_folds_to_space(self) -> None:
        self.assertEqual(clean(f"a{NBSP}b{IDEOGRAPHIC_SPACE}c"), "a b c")

    def test_line_separator_folds_to_newline(self) -> None:
        self.assertEqual(clean(f"a{LINE_SEPARATOR}b"), "a\nb")

    def test_whitespace_normalization_can_be_disabled(self) -> None:
        self.assertEqual(clean(f"a{NBSP}b", normalize_whitespace=False), f"a{NBSP}b")

    def test_typography_is_preserved_by_default(self) -> None:
        text = "don\u2019t \u2014 \u201cquoted\u201d\u2026"
        self.assertEqual(clean(text), text)

    def test_typography_folds_only_on_request(self) -> None:
        text = "don\u2019t \u2014 \u201cquoted\u201d\u2026"
        self.assertEqual(clean(text, typography=True), 'don\'t - "quoted"...')

    def test_ordinary_text_is_untouched(self) -> None:
        text = "def f(x):\n\treturn x + 1  # ok\r\n"
        self.assertEqual(clean(text), text)

    def test_sanitizing_is_idempotent(self) -> None:
        text = f"a{ZWSP}b{RLO}c{NBSP}d{SMUGGLED_TAGS}"
        once = clean(text)
        self.assertEqual(clean(once), once)

    def test_crlf_line_endings_survive(self) -> None:
        self.assertEqual(clean(f"a{ZWSP}\r\nb\r\n"), "a\r\nb\r\n")


def run_cli(script: Path, *args: str, stdin: str | None = None, env: dict | None = None):
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=stdin,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        env=env,
    )


def _locale_env(encoding: str) -> dict:
    """Environment that forces a non-UTF-8 console, as a Windows runner has."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = encoding
    return env


class SanitizeCliTests(unittest.TestCase):
    def test_check_mode_reports_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "dirty.md"
            original = f"a{ZWSP}b\n"
            target.write_text(original, encoding="utf-8")
            result = run_cli(SANITIZER, str(target))
            self.assertEqual(result.returncode, 1)
            self.assertIn("FOUND", result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_write_mode_cleans_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "dirty.md"
            target.write_text(f"a{ZWSP}b\n", encoding="utf-8")
            result = run_cli(SANITIZER, str(target), "--write")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "ab\n")

    def test_clean_tree_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            (Path(raw) / "ok.md").write_text("clean\n", encoding="utf-8")
            result = run_cli(SANITIZER, raw)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_stdin_mode_streams_clean_text(self) -> None:
        result = run_cli(SANITIZER, "--stdin", stdin=f"a{ZWSP}b")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "ab")

    def test_missing_path_fails_closed(self) -> None:
        result = run_cli(SANITIZER, str(Path(tempfile.gettempdir()) / "no-such-dir-xyz"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("ABSTENTION", result.stderr)

    def test_paths_are_required(self) -> None:
        self.assertEqual(run_cli(SANITIZER).returncode, 2)

    def test_stdin_rejects_paths(self) -> None:
        result = run_cli(SANITIZER, "--stdin", ".")
        self.assertEqual(result.returncode, 2)

    def test_extension_filter_skips_other_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            (Path(raw) / "dirty.md").write_text(f"a{ZWSP}b\n", encoding="utf-8")
            result = run_cli(SANITIZER, raw, "--ext", ".py")
            self.assertEqual(result.returncode, 0, result.stderr)


class StreamEncodingTests(unittest.TestCase):
    """A non-UTF-8 console must not let hidden characters survive.

    Regression guard: when the pipeline inherited the ambient locale, the UTF-8
    bytes for U+200B decoded to unrelated code points under cp1252, matched
    nothing, and re-encoded identically, so the sanitizer reported success while
    removing nothing.
    """

    def test_stdin_is_sanitized_under_cp1252(self) -> None:
        result = run_cli(
            SANITIZER, "--stdin", stdin=f"a{ZWSP}b", env=_locale_env("cp1252")
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "ab")

    def test_stdin_is_sanitized_under_latin_1(self) -> None:
        result = run_cli(
            SANITIZER, "--stdin", stdin=f"x{RLO}y", env=_locale_env("latin-1")
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "xy")

    def test_subcommand_stdin_is_sanitized_under_cp1252(self) -> None:
        result = run_cli(
            AIKB,
            "--repo",
            str(REPO),
            "sanitize",
            "--stdin",
            stdin=f"p{ZWSP}q",
            env=_locale_env("cp1252"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "pq")

    def test_newlines_are_not_translated(self) -> None:
        result = run_cli(
            SANITIZER, "--stdin", stdin=f"a{ZWSP}\nb\n", env=_locale_env("cp1252")
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "a\nb\n")


class AikbSanitizeCommandTests(unittest.TestCase):
    def test_subcommand_reports_findings(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "dirty.md"
            target.write_text(f"a{ZWSP}b\n", encoding="utf-8")
            result = run_cli(AIKB, "--repo", str(REPO), "sanitize", str(target))
            self.assertEqual(result.returncode, 1)
            self.assertIn("FOUND", result.stderr)

    def test_subcommand_streams_stdin(self) -> None:
        result = run_cli(
            AIKB, "--repo", str(REPO), "sanitize", "--stdin", stdin=f"x{ZWSP}y"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "xy")

    def test_subcommand_forwards_typography_flag(self) -> None:
        result = run_cli(
            AIKB,
            "--repo",
            str(REPO),
            "sanitize",
            "--stdin",
            "--typography",
            stdin="a\u2014b",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "a-b")


class LauncherExitCodeTests(unittest.TestCase):
    """The Windows launcher must propagate the interpreter's exit code.

    Regression guard: discovery used parenthesised if-blocks, and cmd expands
    %ERRORLEVEL% when it parses a whole block, so the launcher reported the
    result of `where` instead of the result of Python and always exited 0.
    Every failure looked like success to any Windows script or hook.
    """

    LAUNCHER = REPO / "bin" / "aikb.cmd"

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(self.LAUNCHER), "--repo", str(REPO), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

    @unittest.skipUnless(os.name == "nt", "cmd launcher is Windows only")
    def test_success_exits_zero(self) -> None:
        self.assertEqual(self._run("validate").returncode, 0)

    @unittest.skipUnless(os.name == "nt", "cmd launcher is Windows only")
    def test_characterized_failure_exits_two(self) -> None:
        self.assertEqual(self._run("show", "does/not/exist.md").returncode, 2)

    @unittest.skipUnless(os.name == "nt", "cmd launcher is Windows only")
    def test_invalid_subcommand_is_not_reported_as_success(self) -> None:
        self.assertNotEqual(self._run("no-such-command").returncode, 0)

    @unittest.skipUnless(os.name == "nt", "cmd launcher is Windows only")
    def test_sanitize_findings_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            (Path(raw) / "dirty.md").write_text(f"a{ZWSP}b\n", encoding="utf-8")
            self.assertEqual(self._run("sanitize", raw).returncode, 1)


if __name__ == "__main__":
    unittest.main()
