<!-- aikb
{
  "schema_version": 1,
  "claim_id": "spec.engineering.repair.root-cause",
  "namespace": "engineering.repair.root-cause",
  "version": "1.0.0",
  "expression": "A software defect is repaired only when it has a deterministic reproduction, a named root cause and causal chain, coverage of coupled call sites, and a regression check that fails again when the fix is reverted.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "debugging or repairing a software defect in a package, application, service, or library",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "hand-authored-unmeasured",
  "provenance": {
    "producer": "hand-authored://operator",
    "producer_version": "1.0.0",
    "authored_utc": "2026-08-14",
    "derived_from": [
      {
        "source": "Semantic-Interoperability-Framework",
        "locator": "knowledge/engineering.repair.root-cause.python-packages.md sections 1, 2, 4-6",
        "evidence_class": "operator-authored"
      }
    ]
  },
  "lineage": {
    "status": "active",
    "generation": 1,
    "parent_refs": []
  },
  "relationships": [],
  "retrieval": {
    "tags": [
      "debugging",
      "regression",
      "repair",
      "reproduction",
      "root-cause",
      "verification"
    ]
  }
}
-->

# `engineering.repair.root-cause`

> **Authority: hand-authored, unmeasured.** This procedure is a shared base for
> ecosystem specializations. It is not a claim about defect frequencies.

## 1. Reproduce before editing

Do not edit code until the failure happens on demand. Record the exact command,
runtime and dependency versions, relevant environment, working directory, input,
seed, and operating system.

If it does not reproduce, that is the finding: the defect may be environmental,
ordering-dependent, timing-dependent, or data-dependent. Do not replace the
missing reproduction with a speculative patch.

## 2. Build the harness when none exists

A missing test suite is not a reason to verify by hand. Construct the smallest
executable check that fails at the reported symptom. Keep it as a permanent
regression test. Isolate filesystem, process, and network effects unless one of
those effects is the defect being tested.

The harness is a deliverable of the repair, not temporary scaffolding.

## 3. Name the causal chain

Trace from the observed symptom to the first violated contract. Stop only when
you can state:

> root cause at `path:line`, followed by the causal chain that produces the
> symptom.

A patch at the symptom site without that sentence is not a root-cause repair.

Useful localization moves include shrinking the failing input, bisecting
history, promoting warnings to errors, inspecting the exact loaded artifact, and
testing order or concurrency dependence.

## 4. Repair the class, not the instance

Once the cause is named:

1. search for every coupled use of the same construct or contract;
2. fix those sites or explicitly defer each one with a reason;
3. test the edge cases implied by the cause: empty, missing, zero, negative,
   boundaries, duplicates, Unicode, very long inputs, repeated calls,
   concurrency, and failure part-way through;
4. prefer repairing the contract over widening the caller;
5. do not silence the symptom with a broad catch, warning suppression, skipped
   test, or weaker type.

## 5. Withhold "fixed" until adversarial verification

| Tier | Check |
|---|---|
| 1 | The deterministic reproduction now passes. |
| 2 | Revert the fix; the same test fails again. |
| 3 | Coupled sites and implied edge cases have assertions. |
| 4 | A property test covers the violated invariant, the full suite passes, and the check runs in a clean environment built from the real artifact. |

Tier 2 is the minimum for the word **fixed**. Tier 1 supports only "the symptom
was not observed after this change."

## 6. Report shape

Symptom -> exact reproduction and environment -> root cause at `path:line` ->
causal chain -> repair -> coupled sites fixed or deferred -> verification tier ->
residual risk and unverified properties.

## 7. Failure modes

Patching the last traceback frame; wrapping in a broad catch; weakening types;
skipping the failing test; writing an assertion without seeing it fail; reporting
one manual run as proof; repairing one instance while leaving known siblings;
rebuilding the environment without explaining why it helped.

**Falsified if:** repairs satisfying sections 1-5 regress at a rate comparable
to repairs that skip the revert-to-red check.
