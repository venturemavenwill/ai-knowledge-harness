<!-- aikb
{
  "schema_version": 1,
  "claim_id": "finding.browser-agent.osintai",
  "namespace": "engineering.repair.root-cause.browser-agent-integrations",
  "version": "1.0.0",
  "expression": "OSINTai v4.0.0 is a useful design reference for typed evidence records, post-crawl deterministic analysis, falsifiable hypotheses, stage isolation, and findings-level secret omission, but one pipeline path loses model-date provenance, raw crawl archives retain source content, it is not a browser, source-code, or autonomous-agent root-cause system, and it should not be imported as a dependency while the assessed release lacks a license grant.",
  "authority": "reference-only",
  "scope": {
    "holds_when": "evaluating OSINTai v4.0.0 as a design reference or dependency for browser-mediated integration debugging",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "static source review plus isolated test execution; qualitative design assessment",
  "provenance": {
    "producer": "assistant-assessment://operator-authorized",
    "producer_version": "1.0.0",
    "authored_utc": "2026-08-22",
    "derived_from": [
      {
        "source": "https://github.com/gs-ai/OSINTai/tree/61e8fe7e2aab033094d7316c193adf8ec2110496",
        "locator": "v4.0.0 repository tree and source modules under src/osintai, tests, requirements.txt, and .github/workflows/release-gate.yml",
        "evidence_class": "design-reference"
      },
      {
        "source": "assistant-session",
        "locator": "isolated execution on 2026-08-22: Python 3.14 virtual environment, pinned requirements installed, python -W error::ResourceWarning -m unittest discover -s tests -v; 82 tests passed in 4.537 seconds",
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
      "kind": "informs",
      "target": "spec.engineering.repair.root-cause.browser-agent-integrations@1.0.0"
    },
    {
      "kind": "applies",
      "target": "knowledge.harness.evolution"
    }
  ],
  "retrieval": {
    "tags": [
      "design-assessment",
      "evidence-provenance",
      "falsifiability",
      "licensing",
      "osintai",
      "root-cause"
    ]
  }
}
-->

# OSINTai v4.0.0 design assessment

This assessment is pinned to tag `v4.0.0`, commit
`61e8fe7e2aab033094d7316c193adf8ec2110496`, inspected on 2026-08-22.
Later releases can differ.

## Measured snapshot

- repository created 2020-01-11;
- release `v4.0.0` published 2026-08-14;
- GitHub metadata at assessment time: 43 stars, 12 forks, two watchers, one
  listed contributor, and no open issues;
- 27 Python modules under `src/osintai`, approximately 5,586 lines;
- two test files, approximately 972 lines;
- four pinned runtime packages in `requirements.txt`;
- 82 tests passed in 4.537 seconds in an isolated Python 3.14 environment with
  `ResourceWarning` promoted to an error;
- CI declares dependency audit, unit tests, source compilation, security
  analysis, and correctness linting.

These values characterize the assessed release; they are not ecosystem adoption
or code-coverage measurements.

## Verified useful design properties

Static source and test review found:

1. the provenance model defines distinct types for direct observations,
   deterministic derivations, model output, hypotheses, and next-action leads;
2. confidence signals retain their kind instead of being treated as
   interchangeable;
3. hypotheses carry supporting and contradicting evidence plus explicit
   confirmation, refutation, and follow-up fields;
4. post-crawl deterministic stages run independently of optional deep-analysis
   and cross-check stages;
5. one characterized stage failure does not discard prior crawl artifacts or
   prevent independent later analysis;
6. an optional evaluation stage checks model analyses for artifact grounding,
   calibrated language, source discipline, actionable pivots, and output-shape
   compliance;
7. cross-source correlations remain scored candidates rather than silently
   merging identities, and common site-wide entities are filtered;
8. potential secret findings retain type, location, and count rather than the
   matched secret value;
9. the local model endpoint is code-restricted to loopback and fetch redirects
   remain within the configured crawl scope.

The browser-integration specialization independently adapts these functional
ideas into an evidence ledger, a model-grounding gate, contradiction-aware
hypotheses, ubiquitous-boilerplate filtering, bounded stage isolation, and
explicit solution leads.

## Verified provenance and retention caveats

The type system does not guarantee end-to-end origin preservation in every
pipeline path:

- per-page model analysis runs during crawling;
- model-produced `key_dates` are appended to content dates;
- temporal analysis can later emit `DERIVED` findings from that combined date
  stream without retaining which dates came from the model;
- model evaluation is optional and runs after those deterministic stages, so
  it is not a universal admission gate.

The specialization therefore requires observation identifiers and origin to
survive every transformation, and requires grounding checks before a model
claim can contribute to a root-cause finding.

Secret non-retention is limited to analytical findings. The crawler writes full
HTML and extracted page text to raw run artifacts before secret-pattern
analysis. Those archives can contain the original values and require
credential-equivalent access, retention, and deletion controls. The
specialization instead defaults to bounded, sanitized evidence and permits raw
credential-bearing retention only for explicitly approved synthetic data.

## Maturity boundaries

The assessed project is mature in its narrow, local-first OSINT analysis
pipeline, but it is not a general engineering root-cause framework:

- fetching uses HTTP rather than browser automation, so it cannot inspect
  authenticated browser state or JavaScript-only application behavior;
- it does not perform source-code, AST, dependency, diff, or call-graph
  analysis;
- it has no autonomous agent or iterative tool-selection loop;
- no integration tests exercise a real browser or external service;
- the contributor base is one person, so community and adversarial review are
  limited;
- an optional custom model has separate, uncharacterized provenance.
- optional evaluation does not gate every path by which model-derived data can
  influence later findings.

## License and integration decision

The README displays an MIT badge and states "MIT License," but the assessed Git
tree contains no `LICENSE`, `COPYING`, or equivalent file, and GitHub reports no
detected license. A badge and public repository demonstrate probable intent and
permit inspection under the hosting platform's terms; they do not contain the
MIT permission text needed for redistribution or derivative copying.

Consequently:

- retain the pinned repository as a design reference;
- independently express reusable methods and cite the source;
- do not vendor source, copy prose, or add an executable dependency under the
  current release;
- reconsider dependency or source reuse if the copyright holder adds an
  unambiguous license grant or provides permission.

## Verification

Reassess a later tagged release by checking its immutable tree, license file,
dependency lock, tests, CI, browser/code-analysis capabilities, contributor
history, and a clean isolated test run. Upgrade the integration decision only
when the relevant evidence changes.

**Falsified if:** the pinned `v4.0.0` tree contains a valid license grant that
was missed, implements browser automation, source-code analysis, or autonomous
agent orchestration that this assessment classifies as absent, or fails the
reported isolated test command under its pinned dependencies.
