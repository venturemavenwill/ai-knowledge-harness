# Architecture

## 1. Scope

This repository is a portable knowledge harness, not a deployment of the
Semantic Interoperability Layer. It adopts the SIL properties that map cleanly
onto Git:

1. one canonical log of record;
2. append-only facts with explicit supersession;
3. derived, rebuildable read models;
4. explicit namespaces and specialization lineage;
5. conflict preservation;
6. retained source and provenance;
7. surfaced uncertainty and trust boundaries.

It deliberately does not claim SIL properties that Git cannot provide. It has no
codec, latent vector, per-namespace ANN, capability-token service, crypto-shred,
or delivery-time authorization gate.

## 2. Canonical record and projections

The canonical record is the set of files under `namespaces/`, ordered by the Git
commit graph on the protected default branch.

- `namespaces/<id>/manifests/<generation>.json` is append-only namespace
  metadata. A later generation names the prior manifest in `supersedes`.
- `namespaces/<id>/claims/<claim-id>--<version>.md` is an immutable claim. A
  replacement is a new file whose `parent_refs` names what it supersedes or
  revises.
- `catalog.json` and `INDEX.md` are projections. They contain no authority and
  are byte-deterministically rebuilt from the namespace records.

The append-only guarantee is layered:

1. local and CI validation rejects modification, deletion, or rename of an
   existing manifest or claim;
2. pull requests run the history gate against their merge base;
3. GitHub branch protection must reject force-pushes and direct bypasses.

The repository can enforce layers 1 and 2 itself. Layer 3 is an external GitHub
setting. On 2026-08-14, GitHub's branch-protection API returned HTTP 403 for this
private personal repository because the account requires GitHub Pro. Until that
external input changes, the harness installs a local pre-push gate and CI detects
direct-push violations after the fact, but **remote prevention remains
unverified**. Do not describe detection as protection.

## 3. Namespaces and specialization

A namespace is a domain-level routing and provenance boundary. Its active
manifest is the highest valid generation in its `manifests/` directory.

A namespace specializes another by setting:

```json
{
  "extends": "engineering.repair.root-cause"
}
```

Specialization is additive:

- the parent remains independently readable;
- the child narrows activation and adds ecosystem/domain detail;
- a child does not silently overwrite a parent claim;
- `aikb search --namespace <child>` includes ancestors by default so the shared
  procedure and specialization are both visible;
- `--exact-namespace` limits the search to the child only.

Validation rejects missing parents and cycles.

## 4. Retrieval

Every namespace owns its files. `aikb search --namespace` searches only that
namespace and, unless disabled, its declared ancestors.

An unscoped `aikb search` is catalog-level fan-out over independent namespaces.
It is not a global vector index and does not compare raw embeddings across
domains. Results retain their namespace, path, and line provenance. Conflicting
claims are returned as a set; the harness does not average or fuse them.

## 5. Claim record

Each claim is Markdown with a hidden JSON metadata header:

```text
<!-- aikb
{ ... valid JSON ... }
-->
# Human-readable claim
```

JSON is used instead of YAML so the validator and CLI require only the Python
standard library. Claim metadata carries:

- stable `claim_id` and semantic `version`;
- namespace placement;
- expression and scope;
- authority, confidence, and confidence method;
- provenance and retained-source references;
- lineage status, generation, and parent claim references;
- relationships and retrieval tags.

Pre-encoding records cannot contain `z`, `z_ref`, or `codec_version`. Those are
codec outputs and this repository has no codec.

## 6. Trust and instruction safety

All content is reference material. Repository text, search hits, issue text, and
claim bodies are data, even when phrased imperatively. Installed agent surfaces
repeat this boundary.

Authority is explicit:

- `hand-authored-unmeasured`: operator-authored procedure, no numeric confidence;
- `primary-measurement`: measured finding with a retained evidence reference;
- `reference-only`: design or method material that must not activate another
  project's workflow.

No tool may turn source prose into an externally visible action without current
operator intent.

## 7. Determinism

Projection generation:

- sorts namespaces, manifest generations, claims, tags, and routing hints;
- uses repository-relative POSIX paths;
- hashes canonical source bytes with SHA-256;
- emits UTF-8 with LF and one trailing newline;
- contains no clock, hostname, checkout path, or current commit.

`aikb refresh --check` builds projections in memory and byte-compares them with
the checked-in files. CI uses the same code.

## 8. Installation

The checkout remains the source of truth. Installers do not copy knowledge into
another database. They distribute only small routing surfaces and command
wrappers, then point machine-wide agent runtimes back to this checkout.

Updating knowledge is a fast-forward Git pull (`aikb sync`). The command refuses
to run when:

- the checkout has local changes;
- `origin` differs from the canonical remote;
- the pull would require a merge or history rewrite.

## 9. Non-goals and residuals

- GitHub availability and account recovery are external dependencies.
- A private repository does not replace field-level authorization.
- Git history is not immutable against an administrator until branch protection
  and repository governance are configured. The current private-account plan
  does not permit that setting.
- Literal search is not semantic retrieval.
- Curated summaries do not replace retained primary evidence; empirical claims
  must surface when only a summary, rather than the raw result, is present.
- Installation cannot make an agent obey a procedure; verification must come
  from executable checks in the consuming project.
