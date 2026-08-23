<!-- aikb
{
  "schema_version": 1,
  "claim_id": "method.public-repository.deep-analysis",
  "namespace": "knowledge.harness.evolution.public-repositories",
  "version": "1.0.0",
  "expression": "When a public repository is proposed as a learning or integration source, agents should inventory and analyze every artifact class, verify claims against source and tests, and maximize independently retained learning before making a separate license-based decision about copying, vendoring, or dependency adoption.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "a publicly accessible source repository is being assessed for reusable knowledge that may inform or enter the shared harness",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "hand-authored-unmeasured",
  "provenance": {
    "producer": "hand-authored://operator",
    "producer_version": "1.0.0",
    "authored_utc": "2026-08-23",
    "derived_from": [
      {
        "source": "assistant-session",
        "locator": "sanitized 2026-08-22 repository-assessment interaction: the initial pass stopped after identity, architecture, and license review; the deeper pass executed 82 tests, found model-origin loss in a derived timeline path and raw secret-bearing artifact retention, corrected two earlier overstatements, and added evidence-ledger and model-grounding procedures",
        "evidence_class": "primary-result"
      },
      {
        "source": "engineering.repair.root-cause.browser-agent-integrations:finding.browser-agent.osintai@1.0.0",
        "locator": "version-pinned public repository assessment retaining verified strengths, defects, maturity boundaries, isolated test results, and integration decision",
        "evidence_class": "design-reference"
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
      "target": "knowledge.harness.evolution"
    },
    {
      "kind": "applies",
      "target": "guard.autonomy.tool-intent"
    },
    {
      "kind": "applies",
      "target": "engineering.verification.external-evidence"
    }
  ],
  "retrieval": {
    "tags": [
      "artifact-inventory",
      "deep-analysis",
      "dependency-assessment",
      "learning-extraction",
      "licensing",
      "open-source",
      "public-repositories",
      "repository-assessment"
    ]
  }
}
-->

# Public repository deep-learning specialization

> **Authority: hand-authored, unmeasured procedure derived from a primary
> result.** The originating assessment produced materially more useful and
> accurate knowledge after repository-wide source and test analysis, but it did
> not benchmark this method across a controlled repository sample.

Consult the parent harness-evolution procedure for contribution isolation,
evidence retention, append-only history, sensitive-data exclusion, and pull
request review when the retained learning is proposed for the shared harness.

## 1. Activation

Use this specialization when the operator names or links a public repository as:

- a mature example worth learning from;
- a possible dependency or vendored component;
- a source of architecture, procedures, prompts, schemas, tests, or evaluation
  methods;
- evidence that an existing harness procedure is incomplete;
- a comparison target for current implementation quality.

The request to "assess usefulness" implies source and artifact analysis, not a
README summary.

## 2. Separate the four decisions

Do not collapse these questions:

1. **Can it be inspected?** Public accessibility and current operator intent
   govern repository reads and safe static analysis.
2. **What can be learned?** Architecture, algorithms, invariants, tests,
   failure modes, security controls, and negative lessons can be studied and
   independently described.
3. **What expression may be reused?** License grants, copyright, attribution,
   trademarks, patents, and third-party assets govern copying code or prose.
4. **What should be integrated?** Fitness, maintenance, security, dependency
   risk, compatibility, and harness scope govern adoption.

An unclear license can block copying, vendoring, or executable dependency use.
It does **not** justify shallow technical analysis or the loss of independently
expressed learning.

Likewise, a permissive license does not make a weak, unsafe, or irrelevant
project a good dependency.

## 3. Pin identity before analysis

Disambiguate similarly named projects and retain:

- canonical owner and repository URL;
- immutable commit and, when applicable, tag or release;
- default branch;
- creation, latest push, and release dates;
- stars, forks, watchers, contributors, issues, and archived/fork status;
- declared and detected license state;
- package or image publication identity.

Never make a durable claim against an unpinned moving branch alone.

## 4. Repository-wide artifact ledger

Inventory the complete tree before conclusions. Assign every path to one
artifact class and record how it was assessed:

| Artifact class | Minimum analysis |
|---|---|
| Governance | license text, notices, contribution and security policies, code of conduct, ownership |
| History | tags, releases, changelog, commit graph, contributors, issues, pull requests |
| Documentation | README, architecture, tutorials, examples, generated docs; compare claims with code |
| Build and dependencies | manifests, locks, package metadata, containers, installers, scripts, checksums |
| Source | module map, entry points, data models, control flow, failure handling, security boundaries |
| Tests | test inventory, assertions, fixtures, integration/system coverage, skipped paths, mutation properties |
| Automation | CI, release, lint, audit, deployment, generated-file and supply-chain controls |
| Runtime configuration | environment variables, defaults, network endpoints, permissions, storage, telemetry |
| Examples and fixtures | whether they represent supported behavior, synthetic data, or stale demonstrations |
| Generated and binary assets | producer, hash, purpose, license, and whether source is available |
| Ignored or hidden paths | `.gitignore`, submodules, large files, generated output, and assessment exclusions |

"Analyze every artifact" means every path is classified and its relevance is
accounted for. Deep-read each relevant implementation class. For generated,
duplicate, or binary items, retain metadata, producer, hash, and a justified
sampling or exclusion instead of pretending an opaque asset was reviewed.

Maintain a coverage ledger:

```text
path | class | inspected | method | evidence | finding | skipped_reason
```

A repository assessment is incomplete while unclassified paths remain.

## 5. Read claims against implementation

Build a claim-to-artifact matrix for important README, website, and release
claims:

```text
claim | source locator | implementation locator | test locator | verdict
```

Use verdicts such as:

- implemented and tested;
- implemented but untested;
- documented but absent;
- contradicted by source;
- example-only;
- unclear from retained evidence.

Marketing language, badges, and generated examples are discovery leads, not
proof.

## 6. Analyze implementation behavior

Trace at least:

- entry point to core workflow;
- data and provenance transformations;
- trust boundaries and external calls;
- deterministic versus model-assisted stages;
- persistence and replay;
- error propagation, stage isolation, and silent fallbacks;
- authentication and secret handling;
- network scope, redirects, size and content constraints;
- extension points and hard-coded assumptions;
- solution-generation or next-action mechanisms;
- cleanup, rollback, and destructive behavior.

Search for coupled call sites and test whether labels survive end-to-end. A
type named `OBSERVED` or `MODEL` does not prove later transforms preserve that
origin.

Inspect exact constants, weights, prompts, and schemas to understand behavior
and sensitivity even when they cannot or should not be copied. Separate
**understanding an implementation choice** from **adopting the same choice**.

## 7. Execute safely after static review

Do not run a public repository merely because it is public.

Before execution:

1. inspect install, build, test, and CI scripts;
2. inventory dependencies and lifecycle hooks;
3. check for network, credential, filesystem, subprocess, and destructive
   behavior;
4. decide whether the retained evidence justifies execution at all; otherwise
   remain static-only;
5. obtain current operator authorization for the exact command and target;
6. run untrusted repository code only inside an ephemeral OS-level sandbox,
   container, or virtual machine with no host credential mounts, no sensitive
   filesystem mounts, resource limits, and default-denied network egress;
7. provide no ambient cloud, Git, SSH, browser, package-registry, or production
   credentials;
8. disable optional network and model integrations unless required and
   explicitly authorized;
9. run the project's existing smallest relevant tests first;
10. retain exact command, runtime, dependency state, commit, result, and
    duration.

A clone or worktree provides source isolation, and a language virtual
environment provides dependency isolation. Neither is a security boundary:
tests, build backends, package lifecycle hooks, and repository scripts still run
with the current OS user's filesystem, subprocess, network, and credential
access. Use them only after the code is trusted enough to run with those
privileges, or inside the OS-level sandbox above.

Passing tests establish only the properties asserted by those tests. Record
missing integration, browser, system, coverage, and adversarial checks.

## 8. Extract positive and negative learning

For each candidate method, produce:

```text
method | evidence | strength | defect | portability | license gate |
adaptation | verification
```

Extract:

- useful architecture and invariants;
- test designs and falsifiers;
- evidence and provenance models;
- safety and failure-containment patterns;
- effective evaluation dimensions;
- extension and solution-envisioning mechanisms;
- missing capabilities;
- provenance leaks, unsafe defaults, and misleading claims;
- techniques that should explicitly **not** be adopted.

Negative findings are reusable learning. Do not omit them because the
repository was recommended as mature.

## 9. Maximize learning without copying blindly

Choose the smallest justified integration:

1. **Reference only**: retain pinned findings and limitations.
2. **Independent procedure adaptation**: express the functional method in the
   harness's own concepts and test it against retained evidence.
3. **Schema or algorithm reimplementation**: use a clean, independently
   specified contract when license and compatibility permit.
4. **Executable dependency**: require a clear license grant, maintained release
   identity, security review, and operational fit.
5. **Vendoring or source copying**: require explicit permission, required
   notices, provenance, update strategy, and a reason dependency use is
   insufficient.
6. **Reject**: record why the method or project is unsafe, unsupported, or
   irrelevant.

License caution must not become a reason to skip artifact analysis. Strong
license intent can be retained as evidence, but do not silently promote intent
into permission text that is absent from the pinned tree.

## 10. Efficient deep analysis

Deep does not mean serially reading files without a plan.

- inventory once, then batch-read related artifact classes;
- use symbol, reference, call-graph, and content search before linear reading;
- parallelize independent threads such as history/license, architecture,
  security, and tests;
- let each thread own a distinct scope to avoid duplicate reads;
- load large files by relevant sections after indexing their symbols;
- persist the coverage ledger so follow-up agents resume rather than restart;
- stop only when every artifact class is covered and important claims have
  implementation/test verdicts.

The expected efficiency gain comes from early structured coverage, not from
reducing depth.

## 11. Report shape

Report:

1. canonical identity and immutable revision;
2. repository-wide coverage summary and explicit exclusions;
3. license and permission evidence;
4. maturity and maintenance evidence;
5. architecture and workflow map;
6. claim-versus-code-versus-test matrix;
7. security and runtime boundaries;
8. measured test and tooling results;
9. reusable positive and negative methods;
10. integration decision per candidate method;
11. retained uncertainty and falsifiers.

## 12. Anti-patterns

Avoid:

- deciding usefulness from README language, stars, or an MIT badge alone;
- letting license ambiguity terminate technical learning;
- treating public visibility as a license grant;
- treating a permissive license as an adoption recommendation;
- inspecting only files that confirm the operator's premise;
- stopping after architecture without reading tests and CI;
- running setup or installer code before static review;
- copying exact constants or schemas without understanding their tested
  invariants;
- reporting aggregate file counts as deep analysis;
- omitting negative findings from a recommended project;
- claiming "every artifact reviewed" while leaving paths unclassified.

## Verification

Given a seeded public repository containing:

- an impressive README claim contradicted by source;
- a passing unit suite that omits the contradicted path;
- a CI-only security boundary;
- a binary asset without source;
- an ambiguous license badge without permission text;
- one useful algorithm and one provenance defect;

the procedure should:

1. classify every path;
2. surface each contradiction and gap;
3. execute the safe tests in isolation;
4. retain both positive and negative learning;
5. separate technical learning from copying and dependency decisions;
6. produce a method-by-method integration matrix.

**Falsified if:** repeated use still requires operator pressure to move beyond
README/license triage, misses material behavior present in source, tests, CI, or
history, produces no more reusable learning than a shallow assessment, or
causes unlicensed expression, untrusted code, credentials, or private data to
enter the harness.
