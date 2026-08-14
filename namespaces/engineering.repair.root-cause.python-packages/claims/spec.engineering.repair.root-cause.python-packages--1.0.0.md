<!-- aikb
{
  "schema_version": 1,
  "claim_id": "spec.engineering.repair.root-cause.python-packages",
  "namespace": "engineering.repair.root-cause.python-packages",
  "version": "1.0.0",
  "expression": "Python repairs must reproduce in the actual interpreter and built artifact, distinguish import and packaging state from source defects, and test the ecosystem-specific cause rather than patching the surfaced traceback frame.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "debugging or repairing a defect in a Python package, application, or library",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "hand-authored-unmeasured",
  "provenance": {
    "producer": "hand-authored://operator",
    "producer_version": "1.0.0",
    "authored_utc": "2026-08-12",
    "derived_from": [
      {
        "source": "Semantic-Interoperability-Framework",
        "locator": "knowledge/engineering.repair.root-cause.python-packages.md",
        "evidence_class": "operator-authored"
      }
    ]
  },
  "lineage": {
    "status": "active",
    "generation": 1,
    "parent_refs": []
  },
  "relationships": [
    {
      "kind": "specializes",
      "target": "engineering.repair.root-cause"
    }
  ],
  "retrieval": {
    "tags": [
      "debugging",
      "packaging",
      "pytest",
      "python",
      "regression",
      "root-cause"
    ]
  }
}
-->

# `engineering.repair.root-cause.python-packages`

> **Authority: hand-authored, unmeasured.** Consult the parent namespace for the
> shared repair discipline. This child carries Python-specific probes and cause
> families.

## 1. Capture the actual Python environment

Record `sys.executable`, Python version, resolved dependencies (`pip freeze` or
the lockfile), relevant environment variables, working directory, seed, and
operating system.

For import, install, or packaging defects, reproduce in an isolated interpreter
and install the **built wheel or sdist**, not only the working tree. Running from
the checkout can hide missing package data, stale entry points, and `src/` layout
errors.

Use the repository's existing test runner. When none exists, create the smallest
test at the reported symptom and isolate it with temporary paths, environment
patches, and captured logs.

## 2. Python-specific localization

Read tracebacks bottom-up: the last frame is where the defect surfaced, not
necessarily where it originated.

Useful probes:

- shrink the failing input and use `git bisect run`;
- `breakpoint()`, `pdb`, `python -X faulthandler`, or
  `PYTHONFAULTHANDLER=1`;
- `python -W error` to turn a warning into the causal failure;
- `python -c "import m; print(m.__file__, m.__version__)"`;
- `importlib.metadata.version("distribution")`;
- run the failing test alone and in different orders with a fixed
  `PYTHONHASHSEED`.

## 3. Root-cause families

| Family | Signature | Probe |
|---|---|---|
| Import shadowing | local module shadows an installed distribution | inspect `module.__file__` |
| Wrong interpreter | venv inactive, user-site leakage, pip/conda mixing | compare `sys.executable`, `sys.path`, `pip -V` |
| Version skew | installed distribution violates intended resolution | compare lock/metadata with `pip freeze`; use resolver dry-run |
| Stale editable or bytecode | edits have no effect or deleted code runs | reinstall editable; invalidate caches |
| Packaging metadata | checkout works, wheel/sdist fails | install and test the built artifact |
| C extension or ABI | undefined symbol, segfault, incompatible wheel | inspect platform tag and build from source in isolation |
| Module-level state | first call differs; test order matters | inspect import effects, globals, caches, `lru_cache` |
| Mutable defaults | state leaks between calls | inspect list/dict/set default arguments |
| Circular import | partially initialized module | separate runtime imports from type-only imports |
| Async misuse | unawaited coroutine, loop mismatch, hangs | inspect awaits, nested runners, and blocking I/O |
| Encoding or path | local pass, CI or cross-OS failure | make encoding explicit; use `Path`; test case sensitivity |
| Float precision | last-digit assertion failure | use justified tolerance and inspect the algorithm |

These are field-observed patterns, not measured frequencies.

## 4. Verification specialization

In addition to the parent ladder:

- reproduce with the exact interpreter that failed;
- test the installed artifact in a clean environment;
- verify imports resolve to the expected files and distribution versions;
- rerun with caches and editable-install state removed when those are causal;
- cover at least one sibling call site or parameterized instance of the cause.

**Falsified if:** following the parent procedure plus these Python-specific probes
does not improve repair durability over testing only in the working checkout.
