<!-- aikb
{
  "schema_version": 1,
  "claim_id": "method.harness.capture-triggers",
  "namespace": "knowledge.harness.evolution.capture-triggers",
  "version": "1.0.0",
  "expression": "A knowledge harness accumulates agent-originated knowledge only when capture is evaluated at defined checkpoints, because agents reliably retain nothing when retention depends on spontaneously noticing that something was worth retaining.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "an agent is doing primary work inside a project while a durable, human-reviewed knowledge harness is available to it",
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
        "locator": "observation that every claim in this repository through commit 0f4c9f8 originated from an explicit operator instruction rather than an agent proposal",
        "evidence_class": "operator-authored"
      },
      {
        "source": "Live-SWE-agent: Can Software Engineering Agents Self-Evolve on the Fly?",
        "locator": "arXiv:2511.13646v3 (Xia, Wang, Yang, Wei, Zhang; 2025-11-24); reported 77.4% SWE-bench Verified and 45.8% SWE-bench Pro",
        "evidence_class": "reported-summary"
      },
      {
        "source": "OpenAutoCoder/live-swe-agent",
        "locator": "config/livesweagent.yaml at commit 8d7dd8634580d1e09320b4c27d70380bc9ae74a8 (MIT); action_observation_template reflection cue and its length-gated suppression branch",
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
      "kind": "specializes",
      "target": "knowledge.harness.evolution"
    },
    {
      "kind": "depends-on",
      "target": "engineering.verification.external-evidence"
    },
    {
      "kind": "constrained-by",
      "target": "guard.autonomy.tool-intent"
    }
  ],
  "retrieval": {
    "tags": [
      "agent-learning",
      "capture-triggers",
      "harness-evolution",
      "operator-correction",
      "reflection-cadence",
      "self-improvement"
    ]
  }
}
-->

# Capture triggers for reusable capability

> **Authority: hand-authored, unmeasured procedure informed by an external
> reported result.** The external benchmark numbers below were reported by their
> authors and have not been reproduced here. Nothing in this procedure has been
> measured against future agent behavior in this harness. It changes *when an
> agent evaluates* whether to propose knowledge. It does not change who approves
> it, and it is not evidence that any proposal is correct.

Consult the parent procedure for contribution isolation, evidence retention,
append-only history, sensitive-data exclusion, and pull request review. This
specialization governs only the moment at which capture is considered.

## Activation

Evaluate this procedure when primary work reaches one of the checkpoints below.
Do not run it continuously, and do not run it in place of the primary task.

## The failure this addresses

The parent procedure activates "after the primary task has produced direct
evidence of a reusable harness gap" and warns against interrupting work for a
speculative improvement. Both are correct. Together they form an **opportunistic
trigger**: capture happens only when an agent spontaneously notices a gap and
independently judges it non-speculative.

That trigger is unreliable in a specific, predictable way. At the moment work
succeeds, the agent's context is saturated with the solution and the gap that
preceded it has already been resolved. Nothing in the loop asks the question, so
the question is not asked. The observable consequence is that durable knowledge
arrives only when a human notices the gap and dictates it.

An external system provides the contrasting evidence. Live-SWE-agent appends a
fixed reflection cue after every environment observation, asking the agent
whether a tool should be created, and explicitly countering the agent's default
rationalization that basic commands are sufficient. Its reported solve rates
exceed hand-designed scaffolds. The transferable inference is narrow but useful:
**capability generation responds to a scheduled prompt and does not respond to
availability alone.** The harness already has retention machinery; it lacks the
prompt that fires it.

## Capture checkpoints

Evaluate capture at these four points, and otherwise leave it alone.

1. **Verification passed.** The project's authoritative check has just gone from
   failing to passing. Ask what was true about the failure that would not have
   been obvious to a competent agent starting fresh.
2. **The operator corrected the work.** See below; this is the strongest signal
   and the most frequently discarded.
3. **A workaround repeated.** The same non-obvious step was applied a second
   time in this session, or a previously consulted claim was found to be wrong,
   incomplete, or misrouted.
4. **Work was abandoned.** An approach was tried and rejected for a
   characterized reason. A dead end that is retained stops being re-explored.

At each checkpoint, produce one of exactly three outcomes: propose a durable
bridge, record that nothing durable was learned, or report a candidate gap
without acting because operator intent does not currently include harness
modification. Silence is not one of the outcomes.

## Operator correction is primary evidence

When an operator corrects, overrides, redirects, or rejects the agent's work,
that correction is a **primary observation about the operator's authoritative
environment**, with the conversation itself as retained evidence. It is the
closest available analogue to the non-zero return code that drives an external
agent to build a better tool.

Treat it accordingly:

- Record the observable before-and-after behavior, not the agent's account of
  why it erred.
- Distinguish a **correction of fact or procedure**, which may generalize, from
  a **statement of local preference**, which must not leave its project.
- A single correction is enough to justify a proposal. It is not enough to
  justify a numeric confidence, and it never becomes `primary-measurement`
  without a retained executable result.
- Repeated identical corrections across separate sessions are the strongest
  available signal that a durable claim is missing.

Do not capture the operator's private context, credentials, source, or business
detail in order to capture the lesson. If the lesson cannot be expressed without
them, report it and stop.

## What must not be adopted from the external system

The external system's retention model is the inverse of this harness's and must
not be imported. Its artifacts live in a container that is destroyed when the
task ends; there is no cross-task store, no deduplication, no provenance, and no
retention gate beyond a return code. Retaining these distinctions matters more
than the mechanism that was borrowed.

| External behavior | Status here | Reason |
|---|---|---|
| Scheduled cue to build reusable capability | Adopted, bounded to checkpoints | The ignition the harness lacked |
| Task-specific over general artifacts | Already present | Child namespaces specialize without overwriting a parent |
| Retention on exit status alone | Rejected | Retention requires evidence and human review |
| No deduplication of regenerated artifacts | Rejected | Search before adding; extend or supersede an existing claim |
| No provenance on generated artifacts | Rejected | Authority, evidence class, scope, and lineage are mandatory |
| Discarding artifacts at task end | Rejected | The append-only record is the point of the harness |
| Cue suppressed when output exceeds a length bound | Rejected as a defect | The cue disappears exactly when the agent is most overloaded |

The final row is the sharpest negative finding. In the pinned configuration the
reflection cue sits inside a branch taken only when observation output is under
ten thousand characters; longer output replaces it with a truncation warning. A
capture trigger must not ride a channel that silently drops under load. The
checkpoints above are attached to task-phase transitions, which do not.

## Bounds

This procedure raises how often capture is *considered*, which raises the risk of
low-value proposals. Constrain it:

- one proposal per checkpoint at most, and none while the primary task is
  unfinished or unverified;
- search the harness before proposing, and prefer improving routing or adding a
  scoped successor over adding a near-duplicate claim;
- a checkpoint that yields nothing durable is the expected outcome, not a
  failure to find something;
- the human review gate is unchanged; nothing here permits an agent to merge its
  own proposal, and knowledge proposed this way carries no more authority than
  its retained evidence supports.

## Verification

Instrument the checkpoints over a sample of completed sessions and compare
against the current baseline in which agent-originated proposals are effectively
absent. Record, per session: checkpoints reached, proposals raised, proposals
merged, and proposals rejected with the rejection reason. Separately sample
whether merged claims are later retrieved and correctly applied within their
activation scope.

The intended signal is agent-originated proposals that survive independent
review at a rate comparable to operator-originated ones. A rising proposal count
with a falling acceptance rate falsifies the design rather than validating it.

**Falsified if:** checkpoint-driven capture produces proposals that are rejected
substantially more often than operator-initiated ones, degrades primary task
completion, generates near-duplicates of existing claims, causes project-local
preference or sensitive material to be proposed as shared knowledge, or leaves
agent-originated contribution as rare as it was under the opportunistic trigger.
