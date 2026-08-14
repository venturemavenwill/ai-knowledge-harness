<!-- aikb
{
  "schema_version": 1,
  "claim_id": "finding.retrieval.rag.structural-ceilings",
  "namespace": "retrieval.rag.empirical",
  "version": "1.0.0",
  "expression": "On the measured SIL corpus, three gold items had no proximity neighbors at any tested depth, showing that some retrieval ceilings were corpus-structure properties rather than tunable traversal settings.",
  "authority": "reference-only",
  "scope": {
    "holds_when": "diagnosing gold items that remain unreachable across traversal and scoring changes; the count is corpus-specific",
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
        "locator": "research/results/RETRIEVAL-ROUNDS-SUMMARY.md structural ceiling analysis",
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
      "corpus-structure",
      "graph-traversal",
      "rag",
      "recall",
      "retrieval",
      "structural-ceiling"
    ]
  }
}
-->

# Corpus structure can impose a retrieval ceiling

**Evidence status:** reported summary only.

Three gold items on the measured corpus were reported to have no proximity
neighbors at any tested depth. No traversal depth or beam setting can recover a
target that the graph does not connect.

For persistent misses:

1. inspect whether a valid edge or neighborhood exists at all;
2. distinguish unreachable-by-structure from admitted-but-misranked;
3. repair ingestion, relation construction, or source coverage for structural
   misses;
4. do not report a traversal knob as the remedy when no path exists.
