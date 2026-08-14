<!-- aikb
{
  "schema_version": 1,
  "claim_id": "spec.knowledge.finance.evidence-synthesis",
  "namespace": "knowledge.finance.evidence-synthesis",
  "version": "1.0.0",
  "expression": "A financial figure is evidence only with its locator, period, unit, scale, and accounting basis; conflicting figures remain a preserved set; probabilities name their source; and each conclusion clause maps to anchored evidence.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "answering questions from financial filings, reports, decks, tables, or charts where figures must be located, reconciled, and used in a decision-relevant conclusion",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "hand-authored-unmeasured",
  "provenance": {
    "producer": "hand-authored://operator",
    "producer_version": "1.0.0",
    "authored_utc": "2026-08-12",
    "derived_from": [
      {
        "source": "Semantic-Interoperability-Framework",
        "locator": "knowledge/knowledge.finance.evidence-synthesis.md",
        "evidence_class": "operator-authored"
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
      "charts",
      "citation",
      "contradiction",
      "evidence",
      "expected-value",
      "finance",
      "provenance",
      "tables"
    ]
  }
}
-->

# `knowledge.finance.evidence-synthesis`

> **Authority: hand-authored, unmeasured.** This governs evidence handling, not
> investment decisions or advice.

## 1. The anchor rule

A number is evidence only when carried with all of:

| Field | Why it is load-bearing |
|---|---|
| **Locator** | document plus page/section and table row/column, or chart plus series and axis |
| **Period** | fiscal/calendar year, quarter, trailing period, as-of date, and calendar basis |
| **Unit and scale** | currency or other unit, plus thousands/millions/billions |
| **Basis** | GAAP/non-GAAP, reported/constant-currency, gross/net, original/restated, consolidated/segment |

A figure missing period, unit, scale, or basis may not enter a conclusion. Carry
the anchor through every derivation.

## 2. Cross-document comparison

Resolve identity before comparing: entity aliases, legal-name changes, segment
renames, fiscal offsets, acquisitions, divestitures, and restatements.

Never compare different periods or bases without an explicit bridge. State the
normalization and show the reconciling line. When no defensible bridge exists,
report the figures as incomparable.

## 3. Tables and charts

Before reading a chart, inspect:

- logarithmic versus linear scale;
- truncated or non-zero baseline;
- stacked versus grouped values;
- dual axes;
- indexed or rebased series;
- cumulative versus periodic values.

For a table, inspect the units row, footnotes, totals that do not sum, negative
parentheses, exclusions, and the definition of each total.

State what the exhibit cannot answer. A value estimated from an unlabeled point
or a rate inferred from visual slope must be labeled as an estimate.

## 4. Contradiction ledger: never average

Do not merge disagreeing figures into a mean, midpoint, or "best" value.
Averaging manufactures a figure no source states and destroys information.

| Conflict class | Handling |
|---|---|
| Reconcilable period, unit, scale, or basis | Normalize, show the bridge, retain both anchors |
| Supersession or restatement | Prefer the later figure, cite both, state when and why it superseded |
| Transcription error | Cite the upstream source and flag the error |
| Genuine disagreement | Surface the preserved set and explain authority, or state that authority is unresolved |

State when no conflicts were found across the examined document set; do not
leave an empty contradiction ledger implicit.

## 5. Expected-value analysis

1. Enumerate mutually exclusive, collectively exhaustive outcomes and name any
   material residual.
2. Give each probability a source: market-implied, stated guidance, published
   base rate, or operator-provided. Never invent one.
3. Compute expected value with units and horizon; show arithmetic.
4. Identify the input that flips the decision and state its break-even value.
5. Report variance, path dependence, irreversibility, and ruinous downside.

Expected value alone is not a recommendation.

## 6. Evidence-linked conclusion

- Map every conclusion clause to at least one anchored figure, or label it as an
  inference.
- Distinguish verified source readings, derived inferences, and explicit
  assumptions.
- State coverage: what was searched and not found.
- State the specific figure or disclosure that would change the conclusion.

## 7. Failure modes

Scale slips; fiscal/calendar mismatch; silent GAAP/non-GAAP substitution;
averaging conflicts; probabilities without provenance; extrapolation past a
regime change; source-set survivorship; totals containing excluded segments;
rates read from visual slope; restated values compared to originals; analyst
estimates presented as reported facts.

## 8. Verification

| Tier | Check |
|---|---|
| 1 | Every figure carries locator, period, unit, scale, and basis. |
| 2 | Every derived number recomputes from anchored inputs. |
| 3 | Periods, units, and bases agree across comparisons; every bridge is explicit. |
| 4 | Inject a contradicting/restated document or a scale change and assert it is surfaced. |

**Falsified if:** anchor-complete answers are no more accurate than unanchored
answers on a benchmark with known truth, or preserving conflicts degrades
accuracy where a defensible reconciliation existed.
