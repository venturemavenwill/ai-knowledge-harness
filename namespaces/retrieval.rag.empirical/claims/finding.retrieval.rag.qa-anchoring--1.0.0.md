<!-- aikb
{
  "schema_version": 1,
  "claim_id": "finding.retrieval.rag.qa-anchoring",
  "namespace": "retrieval.rag.empirical",
  "version": "1.0.0",
  "expression": "On the measured SIL corpus, generating reader-voice questions per unit and indexing those questions moved R@10 from 0.314 to 0.686 by improving candidate admission rather than reranker scoring.",
  "authority": "reference-only",
  "scope": {
    "holds_when": "considering query-to-unit anchoring for a retrieval corpus; the measured effect is corpus- and model-specific",
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
        "locator": "research/results/RETRIEVAL-ROUNDS-SUMMARY.md round 8C",
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
      "admission",
      "qa-anchoring",
      "query-expansion",
      "rag",
      "recall",
      "retrieval"
    ]
  }
}
-->

# QA anchoring as an admission lever

**Evidence status:** reported summary only; primary artifacts are not yet
vendored in this repository.

The measured intervention generated likely reader questions for each knowledge
unit and indexed those questions alongside the unit. On the measured corpus,
R@10 moved from 0.314 to 0.686.

Transfer the method, not the number:

- evaluate against the target corpus and query classes;
- compare candidate admission before and after anchoring;
- retain the source unit and generation provenance;
- prevent generated questions from becoming a replacement source of truth.
