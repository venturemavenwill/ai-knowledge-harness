from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCAFFOLD = REPO / "scripts" / "new_claim.py"
AIKB = REPO / "bin" / "aikb.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclass resolution requires the module to be importable by name.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


scaffold = _load("new_claim", SCAFFOLD)
aikb = _load("aikb_for_claim_tests", AIKB)


BASE_ARGS = (
    "--title",
    "Retry budgets bound tail latency",
    "--expression",
    "Unbounded retries convert a partial outage into a full one.",
    "--holds-when",
    "a client retries a dependency that is already saturated",
    "--tag",
    "retries",
    "--evidence",
    "operator",
    "incident review 2026-02-11",
    "operator-authored",
)


class ScaffoldTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def make_namespace(
        self,
        namespace: str = "engineering.resilience",
        kind: str = "capability-procedure",
        entry_points: list | None = None,
    ) -> Path:
        directory = self.repo / "namespaces" / namespace
        (directory / "manifests").mkdir(parents=True)
        (directory / "claims").mkdir()
        manifest = {
            "$schema": "../../../schema/namespace-manifest.schema.json",
            "schema_version": 1,
            "namespace": namespace,
            "generation": 1,
            "supersedes": None,
            "title": "Resilience",
            "kind": kind,
            "authority": "hand-authored-unmeasured",
            "extends": None,
            "consult_when": ["a dependency is saturated"],
            "routing_summary": "Bounding retries",
            "capability_summary": "Bound retry behavior under saturation.",
            "entry_points": entry_points or [],
            "search_paths": ["claims"],
        }
        path = directory / "manifests" / "0001.json"
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
        return directory

    def run_scaffold(self, *extra: str, claim_id: str = "spec.retry.budget") -> int:
        argv = [claim_id, "--repo", str(self.repo), "--namespace", "engineering.resilience"]
        argv.extend(BASE_ARGS)
        argv.extend(extra)
        return scaffold.main(argv)

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.email=t@example.com", "-c", "user.name=Test", *args],
            cwd=str(self.repo),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # --- creation -------------------------------------------------------

    def test_creates_claim_named_for_id_and_version(self) -> None:
        directory = self.make_namespace()
        self.assertEqual(self.run_scaffold(), 0)
        claim = directory / "claims" / "spec.retry.budget--1.0.0.md"
        self.assertTrue(claim.is_file())

    def test_body_is_lf_only_with_single_trailing_newline(self) -> None:
        directory = self.make_namespace()
        self.run_scaffold()
        raw = (directory / "claims" / "spec.retry.budget--1.0.0.md").read_bytes()
        self.assertNotIn(b"\r", raw)
        self.assertTrue(raw.endswith(b"\n"))
        self.assertFalse(raw.endswith(b"\n\n"))

    def test_metadata_carries_supplied_evidence_and_scope(self) -> None:
        directory = self.make_namespace()
        self.run_scaffold()
        record = aikb._extract_claim(directory / "claims" / "spec.retry.budget--1.0.0.md")
        self.assertEqual(record.data["namespace"], "engineering.resilience")
        self.assertEqual(record.data["authority"], "hand-authored")
        self.assertIsNone(record.data["confidence"])
        self.assertEqual(
            record.data["provenance"]["derived_from"],
            [
                {
                    "source": "operator",
                    "locator": "incident review 2026-02-11",
                    "evidence_class": "operator-authored",
                }
            ],
        )
        self.assertEqual(
            record.data["scope"]["holds_when"],
            "a client retries a dependency that is already saturated",
        )

    def test_capability_procedure_scaffold_includes_falsifier(self) -> None:
        directory = self.make_namespace(kind="capability-procedure")
        self.run_scaffold()
        body = (directory / "claims" / "spec.retry.budget--1.0.0.md").read_text(encoding="utf-8")
        self.assertIn("**Falsified if:**", body)

    def test_findings_namespace_scaffold_omits_falsifier(self) -> None:
        directory = self.make_namespace(kind="empirical-findings")
        self.run_scaffold()
        body = (directory / "claims" / "spec.retry.budget--1.0.0.md").read_text(encoding="utf-8")
        self.assertNotIn("**Falsified if:**", body)

    # --- the scaffold must not pass as finished knowledge ----------------

    def test_unedited_scaffold_fails_validation(self) -> None:
        directory = self.make_namespace()
        self.run_scaffold()
        record = aikb._extract_claim(directory / "claims" / "spec.retry.budget--1.0.0.md")
        errors: list = []
        aikb._validate_claim(
            self.repo, record, "engineering.resilience", "capability-procedure", errors
        )
        self.assertTrue(
            any("placeholder" in error for error in errors),
            "an unedited scaffold must not validate: {0}".format(errors),
        )

    def test_scaffold_validates_once_the_body_is_written(self) -> None:
        directory = self.make_namespace()
        self.run_scaffold()
        path = directory / "claims" / "spec.retry.budget--1.0.0.md"
        text = path.read_text(encoding="utf-8")
        header, _, _ = text.partition("\n-->\n")
        written = (
            header
            + "\n-->\n\n# Retry budgets\n\nBound total retry attempts per request.\n\n"
            "**Falsified if:** bounded retries do not reduce tail latency.\n"
        )
        path.write_text(written, encoding="utf-8", newline="\n")
        record = aikb._extract_claim(path)
        errors: list = []
        aikb._validate_claim(
            self.repo, record, "engineering.resilience", "capability-procedure", errors
        )
        self.assertEqual(errors, [])

    # --- append-only manifest handling -----------------------------------

    def test_uncommitted_manifest_is_updated_in_place(self) -> None:
        directory = self.make_namespace()
        self.git("init")
        self.run_scaffold()
        manifests = sorted((directory / "manifests").glob("*.json"))
        self.assertEqual([p.name for p in manifests], ["0001.json"])
        manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
        self.assertEqual(manifest["entry_points"], ["claims/spec.retry.budget--1.0.0.md"])

    def test_committed_manifest_gets_a_superseding_generation(self) -> None:
        directory = self.make_namespace()
        self.git("init")
        self.git("add", "-A")
        self.git("commit", "-m", "seed")
        self.assertEqual(self.run_scaffold(), 0)

        manifests = sorted((directory / "manifests").glob("*.json"))
        self.assertEqual([p.name for p in manifests], ["0001.json", "0002.json"])

        original = json.loads(manifests[0].read_text(encoding="utf-8"))
        self.assertEqual(original["entry_points"], [], "committed manifest must not be edited")

        successor = json.loads(manifests[1].read_text(encoding="utf-8"))
        self.assertEqual(successor["generation"], 2)
        self.assertEqual(successor["supersedes"], "manifests/0001.json")
        self.assertEqual(successor["entry_points"], ["claims/spec.retry.budget--1.0.0.md"])

    def test_successor_preserves_existing_entry_points_sorted(self) -> None:
        directory = self.make_namespace(entry_points=["claims/spec.zeta--1.0.0.md"])
        self.git("init")
        self.git("add", "-A")
        self.git("commit", "-m", "seed")
        self.run_scaffold()
        successor = json.loads((directory / "manifests" / "0002.json").read_text(encoding="utf-8"))
        self.assertEqual(
            successor["entry_points"],
            ["claims/spec.retry.budget--1.0.0.md", "claims/spec.zeta--1.0.0.md"],
        )

    def test_absent_git_falls_back_to_a_new_generation(self) -> None:
        directory = self.make_namespace()
        self.run_scaffold()
        self.assertTrue(
            (directory / "manifests" / "0002.json").is_file(),
            "unprovable commit state must fail closed toward append-only",
        )

    def test_enclosing_unrelated_repository_falls_back_to_a_new_generation(self) -> None:
        # The harness checkout is not the Git root here, so HEAD describes a
        # different tree and says nothing about this manifest.
        inner = self.repo / "checkout"
        inner.mkdir()
        self.git("init")
        self.git("add", "-A")
        self.git("commit", "--allow-empty", "-m", "outer")
        self.repo = inner
        directory = self.make_namespace()
        self.run_scaffold()
        self.assertTrue(
            (directory / "manifests" / "0002.json").is_file(),
            "an enclosing repository's HEAD must not be read as proof",
        )

    def test_no_entry_point_leaves_every_manifest_untouched(self) -> None:
        directory = self.make_namespace()
        self.git("init")
        self.assertEqual(self.run_scaffold("--no-entry-point"), 0)
        manifests = sorted((directory / "manifests").glob("*.json"))
        self.assertEqual([p.name for p in manifests], ["0001.json"])
        manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
        self.assertEqual(manifest["entry_points"], [])

    # --- refusals ---------------------------------------------------------

    def test_refuses_unknown_namespace(self) -> None:
        self.make_namespace()
        argv = ["spec.retry.budget", "--repo", str(self.repo), "--namespace", "not.a.namespace"]
        argv.extend(BASE_ARGS)
        self.assertEqual(scaffold.main(argv), 2)

    def test_refuses_to_overwrite_an_existing_claim(self) -> None:
        self.make_namespace()
        self.assertEqual(self.run_scaffold(), 0)
        self.assertEqual(self.run_scaffold(), 2)

    def test_refuses_a_claim_without_retained_evidence(self) -> None:
        self.make_namespace()
        argv = [
            "spec.retry.budget",
            "--repo",
            str(self.repo),
            "--namespace",
            "engineering.resilience",
            "--title",
            "T",
            "--expression",
            "E",
            "--holds-when",
            "H",
            "--tag",
            "retries",
        ]
        self.assertEqual(scaffold.main(argv), 2)

    def test_refuses_confidence_on_a_hand_authored_claim(self) -> None:
        self.make_namespace()
        self.assertEqual(self.run_scaffold("--confidence", "0.9"), 2)

    def test_refuses_measured_authority_without_a_confidence_method(self) -> None:
        self.make_namespace()
        self.assertEqual(self.run_scaffold("--authority", "primary-measurement"), 2)

    def test_refuses_an_invalid_tag(self) -> None:
        self.make_namespace()
        self.assertEqual(self.run_scaffold("--tag", "Not A Tag"), 2)

    def test_refuses_an_invalid_parent_ref(self) -> None:
        self.make_namespace()
        self.assertEqual(self.run_scaffold("--parent-ref", "spec.retry.budget"), 2)

    def test_refuses_an_unsupported_evidence_class(self) -> None:
        self.make_namespace()
        self.assertEqual(
            self.run_scaffold("--evidence", "s", "l", "model-consensus"),
            2,
            "model agreement must never be admissible as an evidence class",
        )

    def test_refuses_a_malformed_version(self) -> None:
        self.make_namespace()
        self.assertEqual(self.run_scaffold("--version", "1.0"), 2)

    # --- invocation -------------------------------------------------------

    def test_runs_as_a_standalone_script(self) -> None:
        self.make_namespace()
        argv = [
            sys.executable,
            str(SCAFFOLD),
            "spec.retry.budget",
            "--repo",
            str(self.repo),
            "--namespace",
            "engineering.resilience",
            *BASE_ARGS,
        ]
        completed = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
