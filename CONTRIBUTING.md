# Contributing to the AI Knowledge Harness

This public repository welcomes contributions from people using any editor,
operating system, or AI assistant. Each contributor needs only a free GitHub
account, Git, and Python 3.9 or newer.

By submitting a contribution, you agree that it may be distributed under the
repository's [MIT License](LICENSE). You remain responsible for reviewing and
licensing any AI-assisted content submitted through your account.

## Collaboration contract

1. Keep the primary checkout on `main` clean so `aikb sync` can fast-forward it
   from the configured canonical remote.
2. Make every change on an `improvement/<slug>` branch in an isolated worktree.
3. Convert project observations into reusable, non-sensitive knowledge. Never
   copy private source, credentials, customer data, or licensed material into
   the harness.
4. Retain evidence and uncertainty. Agreement between multiple models is useful
   review coverage, but it is not primary evidence.
5. Open a pull request. A maintainer reviews and approves every contribution
   they did not author, and CI must pass on every change.
6. Merge by squash, delete the branch, and have every contributor run
   `aikb sync`.

The public repository protects `main` with required pull requests, required
cross-platform CI, linear history, resolved review conversations, and
force-push and deletion restrictions, all enforced for administrators too. The
local pre-push hook catches mistakes earlier, while CI independently validates
canonical history and projections.

While the project has a single maintainer, GitHub cannot require a second
approver for that maintainer's own pull requests, because an author may never
approve their own. The required approval count is therefore zero, and the
maintainer's own changes are gated by CI, the append-only history check, and
public visibility rather than by independent review. The approval requirement
returns as soon as a second maintainer holds write access.

## One-time contributor setup

Fork and clone with GitHub CLI:

```text
gh repo fork venturemavenwill/ai-knowledge-harness --clone
cd ai-knowledge-harness
```

GitHub CLI configures `origin` as your fork and `upstream` as the public
canonical repository. The harness accepts either `origin` or `upstream` as the
canonical source when its URL matches `registry.json`.

Run the platform bootstrap from `README.md` if you also want machine-wide agent
surfaces. The bootstrap is not required to run validation from the checkout.

If you already installed a canonical clone, add your fork as a push remote:

```text
gh repo fork venturemavenwill/ai-knowledge-harness --remote --remote-name fork
aikb contribute concise-gap-slug --push-remote fork
```

## Mixed Windows, macOS, and Linux teams

The harness is supported on all three platforms and CI validates the repository
on each one. Two rules keep a mixed-OS team's canonical records identical:

1. **Canonical records are LF-only.** `.gitattributes` normalizes them and
   `aikb validate` rejects a manifest or claim containing a carriage return.
   This prevents a Windows contributor from producing records whose hashes
   differ from a macOS or Linux checkout.
2. **Use the CLI, not hand-built paths.** `aikb contribute`, `aikb refresh`, and
   the validator emit repository-relative POSIX paths and LF output on every
   platform.

The commands in this guide are identical everywhere. Only the installer differs:
`install/bootstrap.ps1` on Windows and `install/bootstrap.sh` on macOS and
Linux. Both are idempotent and support `--check` and `--uninstall`.

## When an observation qualifies

An agent or contributor may propose a harness improvement when completed work
provides direct evidence of at least one of these conditions:

- the harness has no applicable knowledge for a recurring task;
- existing routing selects the wrong namespace or misses a specialization;
- a documented procedure fails and a verified replacement succeeds;
- installation, validation, or contribution tooling causes reproducible
  friction;
- two grounded findings conflict and the conflict needs to remain visible.

Do not create a contribution for a one-off project convention, an unverified
model suggestion, a personal preference, or information that cannot be safely
retained. If the evidence is incomplete, open a gap issue instead of promoting
the idea into canonical knowledge.

Search before starting:

```text
aikb search "the observed gap"
gh issue list --repo venturemavenwill/ai-knowledge-harness --search "the observed gap"
```

## Start an isolated contribution

From any directory, create a fresh worktree from the current remote `main`:

```text
aikb contribute concise-gap-slug
```

The command refuses a dirty or non-`main` primary checkout, a missing canonical
remote, an existing branch or path, and a worktree nested inside the primary
checkout. It fetches the default branch from the remote whose URL matches
`registry.json`. Use `--push-remote REMOTE` to send the branch to a fork that is
not named `origin`, and `--worktree PATH` when an agent runtime requires a
specific workspace location.

The canonical checkout remains available for normal machine-wide reads while
the contribution worktree contains the proposed change.

## Choose the smallest durable change

| Observation | Contribution |
|---|---|
| General reusable procedure or finding | Add a claim to the applicable namespace. |
| Narrow domain behavior | Add a child namespace with `extends`; do not broaden an unrelated parent. |
| Correction to knowledge | Add a new claim version with `lineage.parent_refs`; never edit the old claim. |
| Namespace metadata change | Add the next manifest generation with `supersedes`. |
| Harness behavior or installation defect | Change code, add a regression test, and update directly related documentation. |
| Plausible gap without retained evidence | File a `Harness gap` issue only. |

Model names, tool versions, prompts, and grounding sources belong in the pull
request when they help reproduce the result. They do not replace the claim's
source, executable checks, or confidence method.

## Verify and submit

Run the complete local gate in the contribution worktree:

```text
python bin/aikb.py --repo . validate
python bin/aikb.py --repo . refresh
python bin/aikb.py --repo . validate --projection
python scripts/check_routing_coverage.py --repo .
python -m unittest discover -s tests -v
git diff --check
```

A new namespace is not finished when it validates. A namespace that declares
`consult_when` must also carry `routing_summary` and `capability_summary` on its
active manifest: the routing table in `surfaces/skill/SKILL.md` and the
capability table in `README.md` are **generated** from those fields by
`aikb refresh`, so they cannot drift from the namespace set. Validation refuses a
routable namespace that omits either, and the generated blocks between
`<!-- BEGIN aikb-routing -->` and `<!-- END aikb-routing -->` must never be
hand-edited. The consult list in
`surfaces/vscode/ai-knowledge-base.instructions.md` remains hand-written prose,
and `check_routing_coverage.py` guards it.

Commit only files that belong to the improvement, then use the push command
printed by `aikb contribute` and open a pull request against the canonical
repository:

```text
git push --set-upstream origin improvement/concise-gap-slug
gh pr create --repo venturemavenwill/ai-knowledge-harness --fill
```

The pull request must explain the observed gap, why it generalizes, the retained
evidence, before/after checks, safety exclusions, and remaining uncertainty.

## Review and integration

The reviewer checks:

- transfer: the change is reusable outside the originating project;
- evidence: the authority and evidence class match what was actually retained;
- isolation: sensitive or project-specific material is absent;
- compatibility: existing namespace behavior and installed surfaces remain
  intact;
- falsifiability: the improvement has a check that could fail;
- plurality: conflicting grounded claims are preserved rather than averaged;
- append-only history: existing canonical records were not edited or deleted.

Different models and tools may review the same pull request to expose blind
spots. Disclose material AI assistance when it helps reproduce or assess the
work. A human reviewer remains accountable for the merge decision. If reviews
disagree, retain the disagreement in the pull request or as separate scoped
claims instead of manufacturing consensus.
