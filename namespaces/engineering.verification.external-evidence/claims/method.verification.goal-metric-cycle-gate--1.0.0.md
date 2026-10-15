<!-- aikb
{
  "schema_version": 1,
  "claim_id": "method.verification.goal-metric-cycle-gate",
  "namespace": "engineering.verification.external-evidence",
  "version": "1.0.0",
  "expression": "An iterative research or improvement loop converges only if each cycle is gated on the goal's own metrics under a fixed, versioned estimand with a preregistered pass and an uncertainty-cleared improvement; engineering success, first measurements and falling lower bounds on a harm are not convergence.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "an autonomous or repeated loop (research factory, optimization campaign, agentic improvement cycle) is expected to make measurable progress toward a stated end goal across cycles",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "hand-authored-unmeasured",
  "provenance": {
    "producer": "hand-authored://operator",
    "producer_version": "1.0.0",
    "authored_utc": "2026-09-28",
    "derived_from": [
      {
        "source": "operator",
        "locator": "2026-09-28 correction of an autonomous research factory: many cycles completed and passed their own engineering gates while no goal metric was defined or moved; operator stated that a factory which runs without converging on the goal is built wrongly",
        "evidence_class": "operator-authored"
      },
      {
        "source": "independent model review of the rebuilt gate",
        "locator": "2026-09-28 critical audit of a first-version scoreboard: (a) a cross-validated classifier leakage lower bound falling across designs was recorded as reduced channel capacity; (b) the gate accepted a cycle whose preregistered acceptance criterion had failed; (c) a local/frontier accuracy ratio compared differently configured systems. All three were adopted as defects; the corrected gate rejects each case in a regression test",
        "evidence_class": "reported-summary"
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
      "convergence",
      "estimand",
      "iteration-gate",
      "lower-bound",
      "preregistration",
      "research-loop",
      "verification"
    ]
  }
}
-->

# Gate each cycle on the goal, not on the work

> **Authority: hand-authored, unmeasured working discipline.** It derives from
> one operator correction and one independent review of a single research loop.
> It states what a convergence gate must reject. It does not claim that any
> particular metric captures a particular goal.

## Activation

Consult this when a loop is supposed to get closer to an end goal across
cycles. Examples include an autonomous research factory, a model or prompt
optimization campaign, a hardening programme, or an agent told to "continue
until X is achieved". Consult it again whenever a cycle report says
"progress".

## The failure

A loop whose cycles are judged by their own engineering outcomes can run
indefinitely without converging. Such outcomes include a harness that finally
ran, a test that passed, a failure that was diagnosed or a result that was
recorded. Every cycle looks productive, yet nothing measures distance to the
goal, so nothing can show that the distance fell.

Three quieter versions survive even after goal metrics are introduced:

1. **A falling lower bound on a harm is read as a falling harm.** A leakage or
   attack-success lower bound is a *falsifier*. A lower value can mean only
   that the observer got weaker, or that fewer samples trained it. It never
   certifies that the underlying quantity decreased. A property like "zero
   leakage" has to come from a construction argument; measurement can only
   refute it.
2. **Numbers are compared across different estimands.** Changing the workload
   set, sample size, task set, scorer, system configuration or observer
   between cycles yields numbers that look comparable but are not.
3. **The numeric gate overrides the preregistered criterion.** A value can move
   in the good direction while the cycle's own preregistered acceptance test
   failed. Recording that as convergence silently replaces the stated test.

## Rule

1. **Define goal metrics before judging cycles.** Each metric needs a target,
   a direction and a versioned estimand stating exactly what is measured, on
   what population, with what observer or scorer. Unmeasured is `null`, never
   0 or 1.
2. **Separate claims that come from construction from claims that come from
   measurement.** Record required construction properties as obligations,
   each verified end to end. Use harm measurements only to falsify those
   obligations.
3. **A first measurement is a baseline, not progress.** A changed estimand
   also starts a new baseline.
4. **Convergence requires all four of these:**
   - the same estimand as before;
   - the cycle's preregistered acceptance passed, with evidence;
   - a difference or paired confidence interval that clears a preregistered
     margin in the improving direction;
   - no regression in any other metric, and every carried-forward value backed
     by an invariance argument or a fresh measurement.
5. **Record everything else explicitly** as no convergence or regression, with
   reasons. The next cycle then changes approach rather than retrying.
6. **Label retroactive rescoring as exploratory.** Rescoring history under a
   new gate is useful, but it is not prospective confirmation.
7. **Treat support work as support.** Harness repair, commissioning and
   diagnosis enable cycles; they do not count as cycles.
8. **Select the next target by gap.** Choose the metric with the largest gap
   to its target, treating an unmeasured metric as the largest gap, rather than
   whatever is easiest to run next.

## Verification

Keep a regression test for the gate that includes each failure case. The gate
must reject:

- a changed estimand;
- a failed preregistered criterion alongside an improved number;
- a confidence interval that crosses the margin;
- a regression in another metric;
- a value carried forward without an invariance argument;
- a lower harm value whose interval does not clear the margin.

Then replay the loop's past cycles through the gate. A loop that had claimed
steady progress but has no cycle surviving the replay has demonstrated the
failure this claim describes.

**Falsified if:** a loop gated this way systematically rejects real, later
independently confirmed progress, or if the gate's requirements cannot be met
by any feasible cycle for the stated goal. The second case would suggest the
goal or its metrics need redefinition, not that the gate should be relaxed.
