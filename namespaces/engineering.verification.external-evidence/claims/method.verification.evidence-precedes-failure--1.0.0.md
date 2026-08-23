<!-- aikb
{
  "schema_version": 1,
  "claim_id": "method.verification.evidence-precedes-failure",
  "namespace": "engineering.verification.external-evidence",
  "version": "1.0.0",
  "expression": "Evidence written only after a run succeeds is absent for every run that fails, so a process must persist its record incrementally and on the error path or it will retain nothing about the outcomes most worth explaining.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "a process produces a durable record of what it did and that record is consumed to diagnose failures or substantiate completion",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "hand-authored-unmeasured",
  "provenance": {
    "producer": "hand-authored://operator",
    "producer_version": "1.0.0",
    "authored_utc": "2026-08-23",
    "derived_from": [
      {
        "source": "SWE-agent/mini-swe-agent",
        "locator": "commit 25941c89cfbc91eb40b3f8756348c91d9977d57e (MIT); src/minisweagent/agents/default.py persists the trajectory in a finally block each step and records an uncaught exception before re-raising",
        "evidence_class": "design-reference"
      },
      {
        "source": "operator",
        "locator": "harness sessions on 2026-08-23 where the retained artifact of a failed step was the only basis for characterizing it",
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
      "kind": "extends",
      "target": "method.engineering.verification.external-evidence"
    }
  ],
  "retrieval": {
    "tags": [
      "diagnosis",
      "evidence-retention",
      "failure-paths",
      "observability",
      "verification"
    ]
  }
}
-->

# Persist evidence before the failure that makes it interesting

> **Authority: hand-authored, unmeasured working discipline.** This states when a
> record must be written. It does not establish that any particular record is
> sufficient evidence; the parent procedure's evidence tiers still govern that.

The parent procedure governs what counts as evidence and what a completion
report must state. This claim governs the timing of the write, which determines
whether any evidence exists at all when a run does not finish.

## Activation

Consult this when designing or reviewing anything that produces a durable record
of its own execution: test and build output, agent trajectories, migration and
deployment logs, batch job results, or the artifacts a gate consults.

## The failure

A record written once at the end of a successful run is written for exactly the
runs that need it least. Every crash, timeout, cancellation, resource exhaustion,
or forced termination produces silence. The outcomes hardest to explain are the
ones that leave nothing behind, so diagnosis falls back to recollection — which
for an agent means reconstructing from context that may itself be gone.

This failure is invisible in normal operation. A pipeline whose evidence is
written only on success looks fully instrumented until the first incident.

## Rule

1. **Write incrementally.** Persist after each meaningful step rather than once
   at the end, so a truncated run still yields everything up to the truncation.
2. **Write on the error path.** Persist in a `finally` or equivalent, so the
   record survives an exception rather than being skipped by it.
3. **Record, then re-raise.** Capture the failure and its context into the
   record, then let the error propagate. Never let recording an error become the
   handler that swallows it — an exception absorbed by its own logging is both
   an unrecorded failure and a false success.
4. **Characterize the stop.** Distinguish completed, failed, limit-exceeded,
   timed-out, and cancelled in the record. A run that stopped because it hit a
   bound is a different observation from one that crashed, and both differ from
   one still running.
5. **Make partial records legible.** A consumer must be able to tell a truncated
   record from a complete one. An incomplete record read as complete is worse
   than no record.
6. **Keep the write cheap and separate.** Evidence writing that is expensive
   gets disabled, and evidence that shares the failing component's fate is not
   independent. Prefer a path that can still succeed when the work fails.

## Relationship to the acceptance gate

The parent procedure holds that a check which could not run is failed or
unverified, never passed. This claim supplies what that determination needs: if
nothing is written when a check cannot run, the absence of a failure record is
indistinguishable from success, and a gate reading that absence silently passes.

Retention timing is therefore a property of gate integrity, not merely of
observability.

## Verification

Interrupt the process partway — kill it, exhaust its budget, force a timeout,
raise inside a step — and confirm the record exists, covers everything up to the
interruption, names the stop reason, and is distinguishable from a completed
run. Confirm the underlying error still propagates to the caller.

Assert this with a test that injects the failure. A record that is only ever
exercised on the success path has not been shown to survive anything.

**Falsified if:** incremental persistence materially degrades the work it
records, produces partial records that consumers misread as complete, or fails
to yield a usable record after an injected interruption.
