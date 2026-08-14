<!-- aikb
{
  "schema_version": 1,
  "claim_id": "finding.retrieval.rag.routing-risk",
  "namespace": "retrieval.rag.empirical",
  "version": "1.0.0",
  "expression": "On the measured SIL corpus, centroid routing over partitioned indexes scored 0.23 versus a 0.31 unpartitioned floor despite 0.66 oracle headroom, making routing accuracy the dominant failure term.",
  "authority": "reference-only",
  "scope": {
    "holds_when": "splitting retrieval into namespaces, shards, or routed partitions; the measured values are corpus-specific",
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
        "locator": "research/results/RETRIEVAL-ROUNDS-SUMMARY.md rounds 9, 10, and 12",
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
      "centroid-routing",
      "namespaces",
      "partitioning",
      "rag",
      "routing",
      "sharding"
    ]
  }
}
-->

# Routing can erase partition headroom

**Evidence status:** reported summary only; the values have not been replayed in
this repository.

The partition scheme had real oracle headroom (0.66), but centroid routing
scored 0.23, below the 0.31 unpartitioned floor.

Before adopting routed shards:

1. score the router independently;
2. compare routed performance with flat retrieval and oracle routing;
3. preserve an abstention or fan-out path for uncertain routes;
4. do not infer partition quality from oracle results while ignoring the real
   router.

The diagnostic method transfers; the numeric values do not.
