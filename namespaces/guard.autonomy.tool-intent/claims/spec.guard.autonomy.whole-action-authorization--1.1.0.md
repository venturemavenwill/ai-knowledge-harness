<!-- aikb
{
  "schema_version": 1,
  "claim_id": "spec.guard.autonomy.whole-action-authorization",
  "namespace": "guard.autonomy.tool-intent",
  "version": "1.1.0",
  "expression": "An authorization predicate is sound when every executable behavior admitted by its accepted input language stays within the grant; exact matching is one sufficient construction, but total character-language restrictions, verified parsing, clause decomposition, and canonicalized containment can also provide whole-action coverage.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "an allow-list, pattern, parser, or policy decides whether an action may run without operator confirmation",
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
        "source": "blind A/B authorization-predicate experiment",
        "locator": "2026-08-23 operator-run experiment: 2 model families, 22-item round plus 8-item hard round; treatment specificity fell 0.25 in both hard-round analyses while sensitivity stayed at ceiling; full method and limitations retained in this claim",
        "evidence_class": "primary-result"
      },
      {
        "source": "SWE-agent/mini-swe-agent",
        "locator": "commit 25941c89cfbc91eb40b3f8756348c91d9977d57e (MIT); the original defect instance remains valid but did not justify surface-syntax generalization",
        "evidence_class": "design-reference"
      }
    ]
  },
  "lineage": {
    "status": "active",
    "generation": 2,
    "parent_refs": [
      "spec.guard.autonomy.whole-action-authorization@1.0.0"
    ]
  },
  "relationships": [
    {
      "kind": "extends",
      "target": "spec.guard.autonomy.tool-intent"
    },
    {
      "kind": "corrects",
      "target": "spec.guard.autonomy.whole-action-authorization@1.0.0"
    }
  ],
  "retrieval": {
    "tags": [
      "allow-list",
      "authorization",
      "empirical-correction",
      "fail-closed",
      "guard",
      "pattern-matching"
    ]
  }
}
-->

# Constrain the complete executable semantics, not a surface prefix

> **Authority: hand-authored, unmeasured procedure corrected by a primary
> result.** A blind A/B experiment falsified the operational guidance in version
> 1.0.0: claim-informed judges over-triggered on hard predicates without
> improving sensitivity. The experiment was small and its oracle had known
> blind spots, so it supports this correction rather than a universal numeric
> confidence.

## Supersession

This version corrects
`spec.guard.autonomy.whole-action-authorization@1.0.0`.

The original worked instance remains valid: a start-anchored allow-list pattern
can authorize an appended shell clause. The overgeneralization was treating
surface syntax such as `re.match`, `startswith`, or a prefix comparison as
evidence of the defect by itself.

That shortcut was falsified. A predicate can use superficially risky syntax and
still constrain the complete executable behavior through an absolute end
anchor, a verified parser, explicit clause decomposition, canonicalized
containment, or an accepted input language whose entire semantics fit inside the
grant. Conversely, `fullmatch` can be unsafe when its pattern contains a
permissive wildcard. The property is semantic, not syntactic.

## Activation

Consult this whenever an allow-list, pattern, parser, cached approval, or policy
decides that an action may proceed without operator confirmation.

Do not activate merely because code contains a particular matching function.
First identify the value being authorized, the transformations applied before
execution, and the exact effect the grant permits.

## Corrected rule

An authorization predicate is sound when **every executable behavior admitted by
its accepted input language remains inside the grant**.

Exact string equality is one sufficient construction, but it is not the
definition. Other constructions can satisfy the rule:

- a regular expression whose *entire language*, not merely its anchors, maps to
  allowed behavior;
- a parser that rejects composition and validates the complete command and every
  argument;
- decomposition into clauses followed by authorization of every clause;
- a restricted character or token language, but only when every value that
  language admits is itself within scope;
- canonicalized path or URL containment using the same representation the
  executor consumes.

A character allow-list that makes shell operators unrepresentable prevents one
injection class but does not prove authorization: `startswith("ls")` can still
admit an unintended executable such as `lsyncd`. Likewise, lexical path
normalization does not establish filesystem containment when symlinks can change
resolution.

## Review procedure

1. **Define the grant as effects.** Name what may happen, not merely which token
   may appear first.
2. **Trace the executed representation.** Check the value after every rewrite,
   expansion, parse, canonicalization, and lookup that occurs before execution.
3. **Characterize the complete accepted language.** Include arguments, suffixes,
   clauses, path traversal, host parsing, wildcards, newlines, and aliases.
4. **Test semantics, not API names.** `re.match` with an absolute end anchor may
   be sound; `fullmatch(r"git log .*", action)` is not.
5. **Generate counterexamples in the input's grammar.** Shell payloads test
   commands, traversal and symlinks test paths, and parsed host variants test
   URLs. A shell-looking string is not a meaningful attack against a path-only
   predicate.
6. **Fail closed on uncharacterized inputs.** If the accepted language cannot be
   bounded, require confirmation rather than widening the grant.

## Empirical correction

The correction was triggered by a pre-registered blind A/B:

- two independent model families judged identical shuffled predicates;
- control judges received only the task, while treatment judges also received
  version 1.0.0;
- labels came from executing pure predicates against a generic bypass battery;
  no payload was executed;
- the easy round contained 22 held-out predicates: 12 defective and 10 sound,
  including five hard distractors;
- the hard round contained eight predicates selected to make surface syntax
  misleading: four defective and four initially labelled sound.

Results:

| Corpus | Control sensitivity / specificity | Treatment sensitivity / specificity |
|---|---:|---:|
| Easy, 22 items | 1.00 / 0.95 | 1.00 / 1.00 |
| Hard, all 8 items | 1.00 / 0.625 | 1.00 / 0.375 |
| Hard, two contested items excluded | 1.00 / 1.00 | 1.00 / 0.75 |

Sensitivity was already at ceiling in every cell, so improvement was not
demonstrated. Treatment specificity fell by 0.25 in both hard-round analyses,
triggering the pre-registered no-go criterion. Version 1.0.0 therefore must not
be used to promote mini-swe-agent-derived guidance harness-wide.

The experiment also exposed two oracle defects before scoring:

- applying shell-composition payloads to path and URL predicates mislabelled
  odd data as executable injection;
- using host-platform path semantics on Windows mislabelled POSIX containment.

Both were corrected before judging. Two remaining treatment flags were
contested because the oracle did not model non-destructive scope violations or
filesystem symlinks. They were excluded in the sensitivity analysis rather than
silently relabelled after seeing the verdicts.

## Limits of the result

The hard round had eight items, two model families, and one run per cell, with no
variance estimate. The oracle was lexical and did not create a filesystem with
symlinks. This is enough to reject version 1.0.0 under its pre-registered gate;
it is not enough to claim that the corrected rule improves AI work. Promotion
beyond this guard remains blocked until a larger, repeated experiment shows
higher sensitivity without material specificity loss.

## Verification

Build a held-out corpus that crosses surface syntax with semantic outcome:

- sound `re.match` and `startswith` constructions;
- defective `fullmatch`, exact-token, and canonicalization constructions;
- command, path, URL, and structured-action inputs;
- real filesystem symlinks for path cases.

Blind multiple model families to the labels, repeat each condition, and compare
the corrected claim with a no-claim control. Pre-register the acceptable change
in sensitivity and specificity before collecting verdicts.

**Falsified if:** reviewers using this procedure still classify predicates from
surface API names instead of accepted semantics, reject sound constructions
more often than an unassisted control, or fail to detect a behavior outside the
grant that an executable counterexample demonstrates.
