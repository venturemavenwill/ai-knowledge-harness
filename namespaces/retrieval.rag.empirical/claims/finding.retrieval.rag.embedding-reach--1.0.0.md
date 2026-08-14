<!-- aikb
{
  "schema_version": 1,
  "claim_id": "finding.retrieval.rag.embedding-reach",
  "namespace": "retrieval.rag.empirical",
  "version": "1.0.0",
  "expression": "In the residual SIL single-fact failures, eight of 35 gold items ranked beyond 200 in first-stage embedding retrieval and were unreachable by any downstream reranker.",
  "authority": "reference-only",
  "scope": {
    "holds_when": "diagnosing residual misses after reranking; the count and rank are corpus-specific",
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
        "locator": "research/results/RETRIEVAL-ROUNDS-SUMMARY.md residual single-fact analysis",
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
      "embedding",
      "first-stage",
      "rag",
      "reach",
      "recall",
      "reranking"
    ]
  }
}
-->

# First-stage reach bounds every reranker

**Evidence status:** reported summary only.

Eight of 35 residual single-fact gold items were reported beyond rank 200 in the
first-stage embedding retrieval. A reranker cannot recover candidates it never
receives.

Measure first-stage rank distributions for missed gold items. When misses are
outside the admitted depth, work on source representation, ingestion,
query-unit anchoring, or the first-stage model before tuning reranker weights.
