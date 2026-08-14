<!-- aikb
{
  "schema_version": 1,
  "claim_id": "finding.retrieval.rag.query-class-inversion",
  "namespace": "retrieval.rag.empirical",
  "version": "1.0.0",
  "expression": "On the measured SIL corpus, reader-voice QA expansion was net-negative on single-fact retrieval but improved six of eight multi-hop cases, so the same retrieval lever changed sign by query class.",
  "authority": "reference-only",
  "scope": {
    "holds_when": "generalizing a query-expansion or retrieval intervention across single-fact and multi-hop query classes",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "reported-summary-primary-artifacts-not-vendored",
  "provenance": {
    "producer": "port://semantic-interoperability-framework",
    "producer_version": "2026-08-14",
    "authored_utc": "2026-08-14",
    "derived_from": [
      {
        "source": "Semantic-Interoperability-Framework",
        "locator": "research/results/RETRIEVAL-ROUNDS-SUMMARY.md query-class comparison",
        "evidence_class": "reported-summary"
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
      "multi-hop",
      "qa-expansion",
      "query-class",
      "rag",
      "single-fact"
    ]
  }
}
-->

# Retrieval effects can invert by query class

**Evidence status:** reported summary only.

Reader-voice QA expansion was reported as net-negative for single-fact
retrieval, while improving six of eight multi-hop cases.

Do not publish one aggregate score when the intervention can change sign:

- define query classes before evaluation;
- report each class separately;
- route or enable the intervention only where measured;
- preserve the no-expansion arm as a control.
