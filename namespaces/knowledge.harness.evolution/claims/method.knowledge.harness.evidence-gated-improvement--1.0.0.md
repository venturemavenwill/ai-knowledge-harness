<!-- aikb
{
  "schema_version": 1,
  "claim_id": "method.knowledge.harness.evidence-gated-improvement",
  "namespace": "knowledge.harness.evolution",
  "version": "1.0.0",
  "expression": "A shared AI knowledge harness improves safely when agents convert verified reusable gaps into isolated, evidence-retaining, append-only pull requests while excluding sensitive and project-specific material.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "AI-assisted work reveals a potentially reusable improvement to this shared Git-backed harness",
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
        "source": "operator",
        "locator": "collaborative harness setup request on 2026-08-14",
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
      "agent-learning",
      "collaboration",
      "evidence-gating",
      "feedback-loop",
      "harness-evolution",
      "pull-requests",
      "specialization"
    ]
  }
}
-->

# Evidence-gated collaborative harness improvement

> **Authority: hand-authored, unmeasured working discipline.** This procedure
> defines a safe contribution loop. It does not establish that any particular
> model output is true or that more contributions necessarily improve agent
> performance.

## Activation

Consult this procedure after the primary task has produced direct evidence of a
reusable harness gap. Qualifying signals include absent knowledge for a recurring
task, incorrect namespace routing, a failed procedure with a verified
replacement, reproducible harness friction, or grounded findings that conflict.

Do not interrupt ordinary work for a speculative improvement. A one-off project
convention, personal preference, model suggestion without retained evidence, or
material that cannot be safely retained does not qualify.

## Procedure

1. **Finish and verify the primary task.** The originating project's
   authoritative checks establish what happened. A plausible agent narrative is
   not evidence.
2. **Search before adding.** Search the harness and open gap issues. If an
   applicable claim exists, improve routing or add a scoped successor instead of
   duplicating it.
3. **Classify the smallest durable bridge.**
   - Add a claim for a reusable procedure or finding.
   - Add a child namespace when the behavior is a narrow specialization.
   - Add a successor claim or manifest generation to correct existing knowledge.
   - Change harness code with a regression test when the gap is executable
     behavior.
   - File an issue only when evidence is incomplete.
4. **Isolate the work.** Run `aikb contribute <slug>` to create an
   `improvement/<slug>` worktree from the current remote default branch. Never
   develop or push directly from `main`.
5. **Generalize without leaking.** Retain safe source locators, observable
   before/after behavior, scope, uncertainty, and tool or model versions needed
   for reproduction. Exclude credentials, customer data, private project code,
   and licensed source material.
6. **Preserve history and plurality.** Existing canonical claims and manifests
   remain unchanged. Corrections use explicit lineage. Conflicting grounded
   claims remain separately scoped; do not average them into artificial
   consensus.
7. **Verify the contribution.** Rebuild projections, run validation and tests,
   and name a check that could falsify the claimed improvement.
8. **Submit for accountable review.** Commit only the bridge, push the feature
   branch, and open a pull request. A named human other than the author reviews
   transfer, evidence, safety, compatibility, and falsifiability before squash
   merge. A single-maintainer project cannot supply that reviewer for the
   maintainer's own change; it then relies on automated gates and public
   visibility, and records that limitation instead of implying independent
   review.

## Cross-model and cross-tool learning

Different models, tools, and grounding sources are useful because their failure
modes and coverage differ. Record that context in the pull request when it aids
reproduction. Independent model agreement is review evidence only; it does not
upgrade a finding to `primary-measurement`. The retained source and executable
result determine authority.

When reviewers disagree, preserve the disagreement in review history or as
separate scoped claims. Resolve it only with stronger evidence, not majority
vote.

## Stop conditions

Abstain from changing the harness and report the candidate gap when:

- current operator intent does not include harness modification;
- source retention would violate confidentiality, privacy, security, or
  licensing constraints;
- the change would import another project's workflow as a global instruction;
- the proposed behavior has not been reproduced or characterized;
- the contribution cannot pass repository validation without weakening an
  existing safety property.

## Verification

For each merged improvement, retain a reproducer or regression check and compare
the relevant outcome before and after the change. Periodically sample whether
future agents retrieve and correctly apply the improvement in its activation
scope without triggering it outside that scope.

**Falsified if:** this process admits sensitive or project-specific material,
causes regressions outside the stated scope, or produces no measurable
improvement in future task outcomes despite repeated correctly routed use.
