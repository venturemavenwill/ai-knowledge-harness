<!-- aikb
{
  "schema_version": 1,
  "claim_id": "design.knowledge.systems.integrity",
  "namespace": "knowledge.systems.integrity",
  "version": "1.0.0",
  "expression": "A knowledge system should preserve conflicting claims, retain source for re-derivation, isolate incomparable namespaces, bound traversal, rebuild projections from its record, and collect data by supersession plus reachability rather than age.",
  "authority": "reference-only",
  "scope": {
    "holds_when": "designing a system that stores, retrieves, reconciles, derives, or garbage-collects knowledge from multiple sources",
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
        "locator": "ARCHITECTURE.md section 11 and docs/agent/ANTIPATTERNS.md",
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
      "autophagy",
      "conflicts",
      "garbage-collection",
      "knowledge-systems",
      "namespaces",
      "provenance",
      "replay"
    ]
  }
}
-->

# Knowledge-system integrity constraints

> **Authority: reference-only design substrate.** These are portable constraints
> derived from SIL. A consuming system must validate them against its own threat
> model and data.

## Preserve plurality

Never average, centroid, or silently select among conflicting claims merely to
produce one answer. A merged value may be a position no source holds. Keep the
conflict-preserved set, provenance, scope, and authority visible to the caller.

## Retain source; do not feed derived output back as truth

Re-derive from retained source. Do not regenerate stored knowledge by decoding,
summarizing, or embedding the system's own prior output and treating it as a new
source. Repeated derived-output ingestion creates model-eats-own-output drift.

When source cannot be retained, surface that limitation and the resulting loss
of replay or correction capability.

## Keep namespace boundaries explicit

Represent domains with distinct namespace metadata and retrieval surfaces.
Vectors or scores from incomparable spaces cannot be safely ranked as though
they share a metric. Cross-namespace work must convert to a comparable
representation before composition.

Catalog-level discovery is different from one global semantic index.

## Bound reads

Traversal "until enough is found" is not a bound. Define explicit depth, beam,
candidate, and work budgets; carry path confidence or provenance; surface a
shortfall instead of silently widening the search.

Any numeric bound must come from a measured deployment input or remain explicit
configuration. Do not present an invented cut as validated.

## One record, rebuildable projections

Choose one authoritative append-only record. Search indexes, catalogs, edges,
and caches are derived read models. Repair them by replay from the record rather
than patching them as independent truth.

Deterministic replay should exclude wall-clock order, host paths, random
iteration order, and hidden mutable state.

## Supersession and garbage collection

Age is not a truth signal. Do not delete knowledge only because it is old.
Collect only when:

1. a later record explicitly supersedes it; and
2. it is no longer referenced or required for provenance, replay, conflict
   history, or legal retention.

## Surface uncertainty

Missing provenance, withheld source, expired scope, uncertain routing, and
unverified derivation must remain characterized through every layer. Silence is
not a safe default.
