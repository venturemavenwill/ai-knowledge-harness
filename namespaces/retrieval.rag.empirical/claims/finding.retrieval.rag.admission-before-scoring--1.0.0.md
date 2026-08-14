<!-- aikb
{
  "schema_version": 1,
  "claim_id": "finding.retrieval.rag.admission-before-scoring",
  "namespace": "retrieval.rag.empirical",
  "version": "1.0.0",
  "expression": "On the measured SIL retrieval corpus, R@10 remained 0.543 across relation-layer and judge changes because the capped candidate pool admitted only 20 of 35 gold items; uncapped reach was 0.914, so admission rather than scoring was binding.",
  "authority": "reference-only",
  "scope": {
    "holds_when": "diagnosing flat recall in a multi-stage retrieval pipeline; the values are corpus-specific and transfer only as a diagnostic prior",
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
        "locator": "research/results/RETRIEVAL-ROUNDS-SUMMARY.md Part A, rounds 7-8B",
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
      "candidate-pool",
      "rag",
      "recall",
      "reranking",
      "retrieval"
    ]
  }
}
-->

# Admission before scoring

**Evidence status:** this record preserves a reported result from the SIL
retrieval summary. The raw result artifacts are not vendored here, so the metric
is reference-only until those artifacts are imported and replayed.

On that corpus:

- relation-layer and judge swaps left R@10 at 0.543;
- the cap-100 candidate pool admitted 20 of 35 gold items;
- uncapped reach was 0.914.

The flat score across scoring changes was the diagnostic signal. Before tuning a
reranker:

1. measure the fraction of gold items that enters the candidate pool;
2. stratify misses by first-stage rank;
3. report capped and uncapped reach;
4. change scoring only after admission headroom is established.

Do not transfer the numeric values as universal thresholds.
