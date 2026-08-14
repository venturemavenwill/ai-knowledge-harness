<!-- aikb
{
  "schema_version": 1,
  "claim_id": "spec.reasoning.rule-induction.grid",
  "namespace": "reasoning.rule-induction.grid",
  "version": "1.0.0",
  "expression": "A latent transformation rule induced from sparse examples must be an explicit parameterized program, reproduce every training pair exactly, separate surviving rivals with a counterexample, and re-derive every parameter on an unseen instance.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "input/output pairs use a formal discrete representation such as two-dimensional grids, state-transition tables, cellular automata, board states, or schema migrations; not general natural-language reasoning",
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
        "locator": "knowledge/reasoning.rule-induction.grid.md",
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
      "arc",
      "counterexample",
      "generalization",
      "grid",
      "hypothesis",
      "rule-induction",
      "state-transition"
    ]
  }
}
-->

# `reasoning.rule-induction.grid`

> **Authority: hand-authored, unmeasured.** This procedure is deliberately
> limited to formal grids and state transitions. Do not generalize it into an
> all-purpose reasoning heuristic.

## 1. Represent before hypothesizing

Encode every pair canonically before guessing a transformation:

- input and output dimensions and their relation;
- symbol or color histograms and the candidate background;
- connected components under both 4- and 8-connectivity;
- object shape, color, cell count, bounding box, position, holes, and symmetry;
- whole-grid axes, periodicity, and motifs;
- the exact diff: cells and objects added, removed, moved, recolored, resized,
  or reordered.

Choosing the wrong object decomposition or connectivity can make a plausible
rule silently wrong.

## 2. Derive invariants first

Across every training pair, list what never varies: dimension relation, palette,
object count, background, symmetry class, and total occupied cells. Invariants
prune the rule space and later become executable output checks.

## 3. Search a named hypothesis vocabulary

- **Geometric:** translate, rotate, reflect, transpose, scale, tile, crop, pad.
- **Topological:** flood fill, fill enclosed regions, count or close holes.
- **Object-level:** select by size, color, uniqueness, count, or position; move,
  align, sort, delete, or recolor.
- **Mapping:** symbol permutation, per-object lookup, size-to-symbol maps.
- **Generative:** complete symmetry, extend lines, repeat a period, denoise.
- **Conditional:** operation selected by an object or grid predicate.
- **Compositional:** apply A then B, only after single operations are rejected.

## 4. Write the rule as a program

Prose is not enough. The rule must expose its parameters:

```text
background := modal_symbol(input)
objects    := components(input, connectivity=4)
largest    := max(objects, key=size)
for object in objects:
    if object != largest:
        recolor(object, color_of(largest))
```

Every constant must be derived from the input. A literal copied from one
training pair is the common shape of a rule that memorizes rather than
generalizes.

## 5. Test counterexamples

1. **Exact reproduction:** produce every training output cell-for-cell. A miss on
   one pair refutes the rule.
2. **Leave-one-out:** induce from all but one pair, then predict the held-out
   pair.
3. **Rivals:** when multiple rules survive, construct an input where they
   disagree. If the supplied data cannot separate them, report the ambiguity and
   prefer the more constrained rule with fewer free parameters.
4. **No lookup-table repairs:** a special case for every training pair means the
   representation or rule is wrong.

## 6. Apply to an unseen instance

- re-run the representation step;
- re-derive every parameter from the unseen input;
- execute the written rule;
- check the result against the invariants;
- if a check fails, repair the rule, never the output by hand;
- report the rule and any surviving rival with the answer.

## 7. Failure modes

Inducing from the first pair and merely confirming the rest; prose without a
program; hard-coded training constants; connectivity mismatch; missing dimension
relations; assuming the modal symbol is always background; "close enough"
outputs; hand-editing output; composing operations too early; treating visual
symmetry as verified symmetry.

## 8. Verification

| Tier | Check |
|---|---|
| 1 | The rule exists in written, parameterized form. |
| 2 | It reproduces every training pair exactly by diff. |
| 3 | Leave-one-out prediction succeeds for each pair. |
| 4 | Rivals are separated by a constructed case or the unresolved ambiguity is reported. |

**Falsified if:** agents following this process do not outperform direct
answering on a held-out grid benchmark, or the no-literals constraint excludes
rules the task family genuinely requires.
