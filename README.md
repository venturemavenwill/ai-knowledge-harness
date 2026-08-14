# AI Knowledge Harness

A private, Git-backed knowledge base that can be cloned onto a new machine and
made available to agents in every project.

The repository is the canonical record. Knowledge is stored as readable Markdown
claims inside explicit namespaces; Git commits preserve history; `catalog.json`
and `INDEX.md` are deterministic projections that can always be rebuilt.

## What this provides

- repository-native, human-readable knowledge claims;
- append-only namespace and claim records, enforced in CI;
- namespace specialization through explicit `extends` relationships;
- namespace-local search plus catalog-level discovery;
- a dependency-free Python CLI (`aikb`);
- machine-wide installation for Copilot, AGENTS.md-compatible tools, Claude, and
  Gemini;
- deterministic validation and projection replay.

This adopts selected SIL architectural properties. It is **not** the SIL runtime:
there is no latent codec, vector database, key service, or authorization plane.
See [ARCHITECTURE.md](ARCHITECTURE.md) for the exact boundary.

## Quick start on this machine

```powershell
python .\bin\aikb.py --repo . validate
python .\bin\aikb.py --repo . list
python .\bin\aikb.py --repo . search "root cause"
python .\bin\aikb.py --repo . lineage engineering.repair.root-cause.python-packages
```

## Install on a new Windows machine

Prerequisites: GitHub CLI authenticated to an account that can read this private
repository, Git, and Python 3.9 or newer.

```powershell
gh repo clone venturemavenwill/ai-knowledge-harness "$HOME\.ai-knowledge-harness\repo"
& "$HOME\.ai-knowledge-harness\repo\install\bootstrap.ps1"
```

Open a new terminal, then:

```powershell
aikb check
aikb search "rerank" --namespace retrieval.rag.empirical
```

Re-running `bootstrap.ps1` repairs drift. `bootstrap.ps1 -Check` writes nothing
and returns non-zero when an installed surface is missing or stale.

## Install on macOS or Linux

Prerequisites: GitHub CLI, Git, and Python 3.9 or newer.

```bash
gh repo clone venturemavenwill/ai-knowledge-harness "$HOME/.ai-knowledge-harness/repo"
"$HOME/.ai-knowledge-harness/repo/install/bootstrap.sh"
```

Ensure `~/.local/bin` is on `PATH`, then run `aikb check`.

## Everyday commands

```text
aikb list
aikb index
aikb search QUERY [--namespace ID] [--exact-namespace]
aikb show PATH [--start N] [--end N]
aikb lineage NAMESPACE
aikb status
aikb check
aikb refresh [--check]
aikb sync
```

`list`, `index`, `search`, `show`, `lineage`, `status`, and `check` are read-only.
`refresh` rewrites only the two generated projections. `sync` fails closed on a
dirty checkout and performs only `git pull --ff-only` from the canonical remote.

## Forming a namespace in GitHub

Create a branch and scaffold the namespace:

```powershell
python .\scripts\new_namespace.py `
  engineering.repair.root-cause.go-packages `
  --title "Go package root-cause repair" `
  --kind capability-procedure `
  --authority hand-authored-unmeasured `
  --extends engineering.repair.root-cause `
  --consult-when "debugging or repairing a defect in a Go package"
```

Copy [templates/claim.md](templates/claim.md) into the new namespace's `claims/`
directory, replace every placeholder, then run:

```powershell
python .\bin\aikb.py validate
python .\bin\aikb.py refresh
python .\bin\aikb.py refresh --check
```

Open a pull request. CI rejects:

- modified or deleted existing namespace manifests or claims;
- broken specialization parents or cycles;
- malformed or path-escaping records;
- hand-authored confidence numbers;
- codec-produced fields in pre-encoding claims;
- stale generated projections.

To change existing knowledge, add a new claim version with `parent_refs`; do not
edit the old claim. To change namespace routing or metadata, add the next manifest
generation with `supersedes`; do not edit the prior manifest.

## Trust boundary

Knowledge is reference material, not an instruction channel. A claim may contain
imperative prose because it documents a procedure; tools and agents must still
reconcile actions with the current operator's intent. Project-specific charters,
build loops, commit conventions, and state files do not become active merely
because this repository describes them.

## Repository map

```text
namespaces/                 append-only namespace manifests and claims
bin/aikb.py                 portable CLI
catalog.json                generated machine-readable projection
INDEX.md                    generated human/agent routing projection
install/                    machine-wide installers
surfaces/                   canonical agent instruction/skill surfaces
schema/                     JSON Schemas for registry, manifests, and claims
scripts/                    namespace scaffolding and history gate
tests/                      deterministic and adversarial checks
```
