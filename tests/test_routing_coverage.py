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
CHECKER = REPO / "scripts" / "check_routing_coverage.py"

SKILL = "surfaces/skill/SKILL.md"
VSCODE = "surfaces/vscode/ai-knowledge-base.instructions.md"
AGENTS = "surfaces/agents/AGENTS-block.md"
README = "README.md"

PARENT = "engineering.repair.root-cause"
CHILD = "engineering.repair.root-cause.python-packages"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_routing_coverage", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_module()


def run_checker(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--repo", str(repo)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


class RoutingCoverageTests(unittest.TestCase):
    """Each case mutates a throwaway copy of the repository."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        for relative in (SKILL, VSCODE, AGENTS, README):
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / relative, target)
        shutil.copytree(REPO / "namespaces", self.repo / "namespaces")
        self.addCleanup(self._tmp.cleanup)

    def _read(self, relative: str) -> str:
        return (self.repo / relative).read_text(encoding="utf-8")

    def _write(self, relative: str, text: str) -> None:
        (self.repo / relative).write_text(text, encoding="utf-8", newline="\n")

    def _drop_lines_matching(self, relative: str, needle: str) -> None:
        kept = [
            line
            for line in self._read(relative).split("\n")
            if needle not in line
        ]
        self._write(relative, "\n".join(kept))

    def test_unmodified_repository_passes(self) -> None:
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_namespace_without_any_route_fails(self) -> None:
        self._drop_lines_matching(SKILL, "guard.output.text-integrity")
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no route for 'guard.output.text-integrity'", result.stderr)

    def test_missing_readme_entry_fails(self) -> None:
        self._drop_lines_matching(README, "knowledge.harness.evolution")
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 1)
        self.assertIn("README.md", result.stderr)

    def test_missing_vscode_entry_fails(self) -> None:
        self._drop_lines_matching(VSCODE, "retrieval.rag.empirical")
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 1)
        self.assertIn("retrieval.rag.empirical", result.stderr)

    def test_parent_is_not_satisfied_by_its_child(self) -> None:
        """A prefix match must not count as a route for the parent namespace."""
        text = self._read(SKILL)
        kept = [
            line
            for line in text.split("\n")
            if not (PARENT in line and CHILD not in line)
        ]
        self._write(SKILL, "\n".join(kept))
        self.assertIn(CHILD, self._read(SKILL))
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"no route for '{PARENT}'", result.stderr)

    def test_typo_is_reported_in_both_directions(self) -> None:
        self._write(SKILL, self._read(SKILL).replace(PARENT, "engineering.repair.root-cuase"))
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"no route for '{PARENT}'", result.stderr)
        self.assertIn("not a routable namespace", result.stderr)

    def test_partial_surface_must_declare_its_deferral(self) -> None:
        text = " ".join(self._read(AGENTS).split())
        self._write(AGENTS, text.replace(checker.DEFERRAL_PHRASE, "only these"))
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 1)
        self.assertIn("reads as complete", result.stderr)

    def test_partial_surface_is_not_required_to_be_exhaustive(self) -> None:
        """The AGENTS block names a subset on purpose; that must stay legal."""
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        named = {
            token
            for token in checker.BACKTICKED.findall(self._read(AGENTS))
            if checker._looks_like_namespace(token)
        }
        self.assertLess(len(named), len(checker.routable_namespaces(self.repo)))

    def test_new_namespace_without_routing_fails(self) -> None:
        """The regression this gate exists for: a namespace merged with no route."""
        namespace = "guard.example.new-capability"
        manifests = self.repo / "namespaces" / namespace / "manifests"
        manifests.mkdir(parents=True)
        (manifests / "0001.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "namespace": namespace,
                    "generation": 1,
                    "supersedes": None,
                    "title": "Example",
                    "kind": "capability-procedure",
                    "authority": "hand-authored-unmeasured",
                    "extends": None,
                    "consult_when": ["an example situation"],
                    "entry_points": [],
                    "search_paths": ["claims"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"no route for '{namespace}'", result.stderr)

    def test_namespace_without_consult_when_is_not_required(self) -> None:
        namespace = "guard.example.unroutable"
        manifests = self.repo / "namespaces" / namespace / "manifests"
        manifests.mkdir(parents=True)
        (manifests / "0001.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "namespace": namespace,
                    "generation": 1,
                    "consult_when": [],
                    "search_paths": ["claims"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_latest_generation_supersedes_earlier_consult_when(self) -> None:
        namespace = "guard.example.superseded"
        manifests = self.repo / "namespaces" / namespace / "manifests"
        manifests.mkdir(parents=True)
        for generation, consult in ((1, ["routable once"]), (2, [])):
            (manifests / f"000{generation}.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "namespace": namespace,
                        "generation": generation,
                        "consult_when": consult,
                        "search_paths": ["claims"],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_namespaces_directory_fails_closed(self) -> None:
        shutil.rmtree(self.repo / "namespaces")
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 2)
        self.assertIn("ABSTENTION", result.stderr)

    def test_missing_surface_fails_closed(self) -> None:
        (self.repo / SKILL).unlink()
        result = run_checker(self.repo)
        self.assertEqual(result.returncode, 2)
        self.assertIn("ABSTENTION", result.stderr)


class FileNameTokenTests(unittest.TestCase):
    def test_dotted_file_names_are_not_treated_as_namespaces(self) -> None:
        for token in ("catalog.json", "INDEX.md", "llms.txt", "aikb.py"):
            self.assertFalse(checker._looks_like_namespace(token.lower()), token)

    def test_real_namespaces_are_recognized(self) -> None:
        for token in (PARENT, CHILD, "guard.output.text-integrity"):
            self.assertTrue(checker._looks_like_namespace(token), token)


if __name__ == "__main__":
    unittest.main()
