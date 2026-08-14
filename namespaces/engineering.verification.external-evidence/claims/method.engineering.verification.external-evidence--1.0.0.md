<!-- aikb
{
  "schema_version": 1,
  "claim_id": "method.engineering.verification.external-evidence",
  "namespace": "engineering.verification.external-evidence",
  "version": "1.0.0",
  "expression": "A claim that work is done or correct must come from an external check, and acceptance should climb from structure through integration and specification to adversarial mutation rather than accumulating low-tier clean runs.",
  "authority": "reference-only",
  "scope": {
    "holds_when": "deciding whether software, a gate, or an agent-produced artifact is complete, correct, or sufficiently verified",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "design-reference",
  "provenance": {
    "producer": "port://semantic-interoperability-framework",
    "producer_version": "2026-08-14",
    "authored_utc": "2026-08-14",
    "derived_from": [
      {
        "source": "Semantic-Interoperability-Framework",
        "locator": "docs/agent/CHARTER.md sections 2 and 4; docs/agent/GATE_TEMPLATE.md",
        "evidence_class": "design-reference"
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
      "acceptance",
      "adversarial",
      "evidence",
      "gates",
      "integration",
      "mutation",
      "verification"
    ]
  }
}
-->

# External evidence and verification ladders

> **Authority: reference-only.** This is portable working discipline extracted
> from another project's charter. It does not activate that project's build loop,
> state files, milestone IDs, or commit conventions.

## 1. Self-assessment is not evidence

Confidence in one's own output does not establish quality. The words **done**,
**correct**, **fixed**, and **good enough** require an external mechanism:

- a test observed failing before the repair and passing after it;
- a deterministic replay that reproduces bytes;
- a contract or type check;
- a mutation test proving the gate detects a broken implementation;
- an independently measured acceptance result.

When no external check exists, report the property as **unverified** rather than
converting confidence into evidence.

## 2. Evidence tiers do not add linearly

Many clean runs remain low-tier evidence when they do not exercise the property
directly. A higher-tier property test, replay, or structural proof can dominate
hundreds of incidental runs. Buy the highest evidence tier available; do not let
volume justify skipping it.

## 3. Four-tier acceptance gate

1. **Structural:** required files and symbols exist; unit tests and static checks
   pass. Necessary, never sufficient.
2. **Integration seam:** a real caller invokes the feature. This catches the
   common failure where a correct module is never wired into behavior.
3. **Specification deliverable:** every acceptance criterion has an executable
   reproduction tied to the authoritative requirement.
4. **Adversarial and mutation:** intentionally break invariant-enforcing code and
   show the gate turns red; test hostile and boundary inputs.

When a real integration environment exists, add crash, concurrency, replay, and
soak checks above these tiers.

## 4. Gate integrity

- Never weaken a gate to make it pass.
- Never turn a fail-closed default into a pass.
- Record a defect, write its regression test first, then repair it.
- A surviving mutant in the claimed property means the gate is decorative.
- A check that could not run is failed or unverified, never passed.
- Record what a gate does **not** prove.

## 5. Completion report

State:

- authoritative requirement;
- checks run and their evidence tiers;
- integration seam exercised;
- adversarial or mutation evidence;
- properties still unverified;
- residual risks and the input that would falsify the conclusion.
