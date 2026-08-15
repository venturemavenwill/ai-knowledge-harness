from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AIKB = REPO / "bin" / "aikb.py"

SKILL = "surfaces/skill/SKILL.md"
README = "README.md"
GUARD = "guard.autonomy.tool-intent"
RENDERED = "engineering.verification.external-evidence.rendered-artifacts"


def _load_aikb():
    spec = importlib.util.spec_from_file_location("aikb_under_test", AIKB)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules, so register first.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


aikb = _load_aikb()


def run_aikb(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(AIKB), "--repo", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


class GeneratedRoutingTests(unittest.TestCase):
    """Each case works on a throwaway copy of the repository."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        for name in ("registry.json", "catalog.json", "INDEX.md", README):
            shutil.copy2(REPO / name, self.repo / name)
        for tree in ("namespaces", "schema", "surfaces"):
            shutil.copytree(REPO / tree, self.repo / tree)
        self.addCleanup(self._tmp.cleanup)

    def _read(self, relative: str) -> str:
        return (self.repo / relative).read_text(encoding="utf-8")

    def _write(self, relative: str, text: str) -> None:
        (self.repo / relative).write_text(text, encoding="utf-8", newline="\n")

    def _manifest_path(self, namespace: str) -> Path:
        manifests = sorted((self.repo / "namespaces" / namespace / "manifests").glob("*.json"))
        return max(
            manifests,
            key=lambda p: json.loads(p.read_text(encoding="utf-8"))["generation"],
        )

    def test_baseline_is_current(self) -> None:
        self.assertEqual(run_aikb(self.repo, "refresh", "--check").returncode, 0)

    def test_generation_is_idempotent(self) -> None:
        before = (self._read(SKILL), self._read(README))
        self.assertEqual(run_aikb(self.repo, "refresh").returncode, 0)
        self.assertEqual((self._read(SKILL), self._read(README)), before)

    def test_hand_edit_of_generated_block_is_stale(self) -> None:
        self._write(SKILL, self._read(SKILL).replace(
            "Before any non-read tool action", "Whenever you feel like it"
        ))
        self.assertEqual(run_aikb(self.repo, "refresh", "--check").returncode, 1)
        self.assertEqual(run_aikb(self.repo, "validate", "--projection").returncode, 1)

    def test_refresh_restores_a_hand_edited_block(self) -> None:
        original = self._read(SKILL)
        self._write(SKILL, original.replace(
            "Before any non-read tool action", "Whenever you feel like it"
        ))
        self.assertEqual(run_aikb(self.repo, "refresh").returncode, 0)
        self.assertEqual(self._read(SKILL), original)

    def test_refresh_restores_a_deleted_row(self) -> None:
        original = self._read(SKILL)
        self._write(SKILL, "\n".join(
            line for line in original.split("\n") if RENDERED not in line
        ))
        self.assertEqual(run_aikb(self.repo, "refresh").returncode, 0)
        self.assertEqual(self._read(SKILL), original)

    def test_prose_outside_the_block_is_preserved(self) -> None:
        marker = "Search before asserting."
        self.assertIn(marker, self._read(SKILL))
        self._write(SKILL, self._read(SKILL).replace(marker, "Search first, always."))
        self.assertEqual(run_aikb(self.repo, "refresh").returncode, 0)
        self.assertIn("Search first, always.", self._read(SKILL))

    def test_missing_markers_fail_closed(self) -> None:
        self._write(SKILL, self._read(SKILL).replace(aikb.ROUTING_BEGIN, ""))
        result = run_aikb(self.repo, "refresh", "--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing routing markers", result.stderr)

    def _add_namespace(self, namespace: str, **extra: object) -> None:
        manifests = self.repo / "namespaces" / namespace / "manifests"
        manifests.mkdir(parents=True)
        (self.repo / "namespaces" / namespace / "claims").mkdir(parents=True)
        record = {
            "schema_version": 1,
            "namespace": namespace,
            "generation": 1,
            "supersedes": None,
            "title": "Scratch",
            "kind": "capability-procedure",
            "authority": "hand-authored-unmeasured",
            "extends": None,
            "consult_when": ["an example situation"],
            "entry_points": [],
            "search_paths": ["claims"],
        }
        record.update(extra)
        (manifests / "0001.json").write_text(
            json.dumps(record, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def test_routable_namespace_without_summaries_is_rejected(self) -> None:
        """The regression this design exists for: it must be impossible to merge."""
        self._add_namespace("guard.example.scratch")
        result = run_aikb(self.repo, "validate")
        self.assertEqual(result.returncode, 1)
        self.assertIn("routing_summary", result.stderr)
        self.assertIn("capability_summary", result.stderr)

    def test_namespace_with_summaries_routes_itself(self) -> None:
        self._add_namespace(
            "guard.example.scratch",
            routing_summary="An example situation arises",
            capability_summary="Demonstrate generated routing.",
        )
        self.assertEqual(run_aikb(self.repo, "validate").returncode, 0)
        self.assertEqual(run_aikb(self.repo, "refresh").returncode, 0)
        self.assertIn("An example situation arises", self._read(SKILL))
        self.assertIn("Demonstrate generated routing.", self._read(README))

    def test_unroutable_namespace_is_not_required_to_have_summaries(self) -> None:
        self._add_namespace("guard.example.scratch", consult_when=[])
        self.assertEqual(run_aikb(self.repo, "validate").returncode, 0)

    def test_summary_with_a_pipe_is_rejected(self) -> None:
        """A pipe would corrupt the generated markdown table."""
        self._add_namespace(
            "guard.example.scratch",
            routing_summary="broken | column",
            capability_summary="Demonstrate generated routing.",
        )
        result = run_aikb(self.repo, "validate")
        self.assertEqual(result.returncode, 1)
        self.assertIn("must not contain", result.stderr)

    def test_overlong_summary_is_rejected(self) -> None:
        self._add_namespace(
            "guard.example.scratch",
            routing_summary="x" * 121,
            capability_summary="Demonstrate generated routing.",
        )
        result = run_aikb(self.repo, "validate")
        self.assertEqual(result.returncode, 1)
        self.assertIn("at most 120 characters", result.stderr)

    def test_superseded_generation_may_omit_the_summaries(self) -> None:
        """Generation 1 predates the fields and is immutable, so it must stay valid."""
        path = self._manifest_path(GUARD)
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertGreater(record["generation"], 1)
        first = json.loads(
            (path.parent / "0001.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("routing_summary", first)
        self.assertEqual(run_aikb(self.repo, "validate").returncode, 0)


class RoutingOrderTests(unittest.TestCase):
    def test_guards_sort_before_other_roots(self) -> None:
        ordered = sorted(
            [
                "knowledge.systems.integrity",
                "engineering.repair.root-cause",
                "guard.autonomy.tool-intent",
                "retrieval.rag.empirical",
            ],
            key=aikb._routing_sort_key,
        )
        self.assertEqual(ordered[0], "guard.autonomy.tool-intent")
        self.assertEqual(ordered[-1], "knowledge.systems.integrity")

    def test_specialization_follows_its_parent(self) -> None:
        parent = "engineering.verification.external-evidence"
        ordered = sorted([RENDERED, parent], key=aikb._routing_sort_key)
        self.assertEqual(ordered, [parent, RENDERED])

    def test_unknown_root_sorts_last_deterministically(self) -> None:
        ordered = sorted(
            ["zzz.unknown.thing", "guard.autonomy.tool-intent", "aaa.unknown.thing"],
            key=aikb._routing_sort_key,
        )
        self.assertEqual(ordered[0], "guard.autonomy.tool-intent")
        self.assertEqual(ordered[1:], ["aaa.unknown.thing", "zzz.unknown.thing"])


if __name__ == "__main__":
    unittest.main()
