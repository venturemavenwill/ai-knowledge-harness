<!-- aikb
{
  "schema_version": 1,
  "claim_id": "finding.retrieval.rag.exhausted-levers",
  "namespace": "retrieval.rag.empirical",
  "version": "1.0.0",
  "expression": "On the measured SIL corpus, cheap knob sweeps, centroid routing, multi-grain QA blending, cap widening, and structural self-assembly failed to improve the binding retrieval limit and should not be rerun without a changed hypothesis or substrate.",
  "authority": "reference-only",
  "scope": {
    "holds_when": "proposing another retrieval experiment on the same or materially similar substrate; each lever must be re-measured on a different corpus",
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
        "locator": "research/results/RETRIEVAL-ROUNDS-SUMMARY.md known-exhausted list",
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
      "exhausted-levers",
      "experiments",
      "negative-results",
      "rag",
      "retrieval"
    ]
  }
}
-->

# Preserve negative retrieval results

**Evidence status:** reported summary only.

The measured program marked these paths as exhausted on its substrate:

- cheap scoring and parameter sweeps;
- centroid routing;
- multi-grain QA blending;
- merely widening the candidate cap;
- structural self-assembly.

A negative result is reusable knowledge only within its scope. Before rerunning
one of these paths, state what changed: corpus, model, query class, admission
mechanism, routing authority, or falsifiable hypothesis. Do not spend another
round on the same substrate merely because the earlier failure is inconvenient.
