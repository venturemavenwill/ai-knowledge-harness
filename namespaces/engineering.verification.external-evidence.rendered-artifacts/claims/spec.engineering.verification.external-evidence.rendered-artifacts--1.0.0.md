<!-- aikb
{
  "schema_version": 1,
  "claim_id": "spec.engineering.verification.external-evidence.rendered-artifacts",
  "namespace": "engineering.verification.external-evidence.rendered-artifacts",
  "version": "1.0.0",
  "expression": "When a deliverable's correctness is only observable once rendered, object-model success is structural evidence only; the work must be driven through an addressable, re-runnable transform over explicitly selected source items and accepted on inspected renders plus machine-checkable layout, coverage, and residue invariants.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "producing or modifying an artifact whose acceptance depends on rendered appearance, including decks, documents, spreadsheets, diagrams, and generated reports",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "hand-authored-unmeasured",
  "provenance": {
    "producer": "hand-authored://operator",
    "producer_version": "1.0.0",
    "authored_utc": "2026-08-15",
    "derived_from": [
      {
        "source": "assistant-session",
        "locator": "rebuild of a 52-item presentation by reuse from a 768-item, 18-file corpus; Windows office-suite COM automation; two attempts on 2026-08-15, first rejected by the operator and second accepted",
        "evidence_class": "primary-result"
      }
    ]
  },
  "lineage": {
    "status": "active",
    "generation": 1,
    "parent_refs": []
  },
  "relationships": [
    {
      "kind": "specializes",
      "target": "engineering.verification.external-evidence"
    },
    {
      "kind": "applies",
      "target": "engineering.repair.root-cause"
    },
    {
      "kind": "applies",
      "target": "guard.output.text-integrity"
    }
  ],
  "retrieval": {
    "tags": [
      "acceptance-gate",
      "asset-reuse",
      "deck",
      "document-automation",
      "layout-invariants",
      "office-automation",
      "presentation",
      "rendered-artifacts",
      "slides",
      "template-reuse",
      "visual-verification"
    ]
  }
}
-->

# `engineering.verification.external-evidence.rendered-artifacts`

> **Authority: hand-authored, unmeasured.** Consult the parent namespace for the
> evidence tiers and gate integrity rules. This child carries the production and
> acceptance specialization for artifacts that are only correct if they look
> correct. Derived from a single observed rebuild task, not from a controlled
> comparison.

**Applies to:** slide decks and presentations (PowerPoint, Keynote, Google
Slides), word-processing documents (Word, Docs), spreadsheets (Excel, Sheets),
diagrams, PDFs, generated HTML reports, and any template-driven deliverable
where an operator accepts or rejects the artifact by looking at it. It applies
whether the artifact is built by office-suite automation, a document library, or
a headless renderer.

## 1. Classify the instruction before choosing a method

"Reuse", "modify", "adapt", "harvest", or "start from the existing X" is a
**retrieval-and-transform** instruction. It is not satisfied by generating new
content that merely resembles the source, however attractive the result.

Discriminating test: for each element of the output, name the specific source
item it came from. If that mapping cannot be stated, the work is generation
wearing the vocabulary of reuse.

The observed failure was to treat corpus items as backgrounds: delete their
content, then redraw replacement content at hardcoded coordinates. In slide
terms, the template deck was kept only as wallpaper while a new deck was
hand-painted on top. Every automated signal was green and the requirement was
still unmet, because the retained material was the wallpaper rather than the
design.

State the interpretation and its consequences before building. When an
instruction could be read as either reuse or generation, resolve it with the
operator rather than picking the one that is easier to execute.

## 2. Make the source corpus addressable before selecting from it

Do not select from the first plausible source item. Enumerate the corpus, then
make it searchable in both modalities:

- render every candidate item to an image;
- extract per-item text into one greppable index;
- build labelled composite sheets so candidates can be compared cheaply by eye.

Selection then becomes an explicit matching table: for each required output
beat, record the chosen source item and the reason. That table, not the build
script, is the artifact the operator can review and correct.

Indexing an entire corpus up front is usually cheaper than a wrong structural
choice discovered after the artifact is built.

## 3. Prefer structural import over redrawing

Use the platform's native operation for bringing an existing item into the
target — importing a slide, inserting a source document, copying a styled sheet
— because it carries theme, layout, master, and styling with it. Redrawing
discards precisely the design fidelity that made reuse the requirement, and it
converts every later correction into code editing.

Confirm fidelity by rendering immediately after import and before any content
edits, so design loss and content loss cannot be confused later.

## 4. Make the artifact's edit surface explicit

Before writing any edit, dump a complete inventory of addressable slots — item,
container path, field; for a deck this is slide, shape or group path, and
paragraph or table cell — and treat that address space as the interface.

Express the changes as declarative data keyed to that address space, applied by
one idempotent script. The payoff is not elegance: it makes a fix a data edit
plus a re-run, which is the only way the verify loop stays cheap enough to be
repeated as often as this class of work requires.

## 5. Prove edit coverage rather than assuming it

Diff the slot inventory against the edit coverage. Every uncovered slot still
holds source content and must be explicitly replaced, deleted, or consciously
accepted.

Partial-field replacement is a silent hazard. Writing the first *n* sub-elements
of a field can leave the remainder of the original in place, and in some APIs
writing the final sub-element inserts rather than replaces. Both produce hybrid
output that reads as plausible and is wrong. Truncate or clear the remainder,
then assert the post-write element count matches the intent.

## 6. Acceptance specialization

Map the parent's four tiers onto the rendered medium:

| Parent tier | Rendered-artifact form |
|---|---|
| Structural | the transform completes without warnings; the file saves and reopens |
| Integration seam | every item renders to an image **and the images are actually viewed** |
| Specification deliverable | each required beat is located in the render and matches the requirement |
| Adversarial and invariant | machine-checkable assertions that can turn red |

A transform that reports zero warnings has produced structural evidence only.
The render is the integration seam; an unviewed render is not evidence.

Cheap objective invariants worth asserting on every pass:

- **Geometry:** no content extends past the canvas — flag any element where
  `top + height` exceeds canvas height, or the horizontal equivalent.
- **Residue:** extract all text and search for source-corpus vocabulary that
  must not survive — organisation names, product names, citations, footnotes.
- **Completeness:** rendered item count equals the intended count.
- **Text integrity:** run the harness sanitizer over generated content before
  it is written or published.

These catch precisely what a narrative summary hides, and they cost seconds.

## 7. Repair at the transform, not at the artifact

When several items show the same defect, the cause is normally one rule in the
transform. Fix the rule and re-run. Hand-patching each rendered item destroys
reproducibility, leaves the systematic cause live, and reintroduces the defect
on the next build.

In the observed task, one corrected rule about replacing field sub-elements
removed residual source text across the whole artifact, and one layout-fitting
rule repaired every oversized table at once.

## 8. Treat delegated visual inspection as leads, not findings

Sub-agent reports on composite images misattribute item identity often enough
to be untrustworthy as a work order. Label every item inside the composite, and
independently confirm any specific item before acting on it. A delegated report
is a list of candidates to verify.

Its value is recall, not precision: it is worth running because it surfaces
defects the author has stopped seeing, not because its item numbers are right.

## Verification

Retain the selection table, the slot inventory, the declarative edit data, and
the invariant checks. Re-running the transform from those inputs must reproduce
the accepted artifact.

Before declaring completion, state which tier each property reached, and name
any property that was accepted on inspection alone.

**Falsified if:** artifacts produced through corpus indexing, structural import,
declarative editing, and rendered plus invariant acceptance show no durability
or rework advantage over direct generation with unviewed automated checks.

## Limitations

Derived from one task on one platform, observed and written up by the assistant
that performed the successful attempt. There was no controlled re-run, no
independent scoring, and no separation of method effects from model effects.
Treat the procedure as a transferable working discipline, not as a measured
result, and do not cite it as evidence that any particular model or tool is
superior.
