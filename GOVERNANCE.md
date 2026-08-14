# Governance

## Project goal

AI Knowledge Harness exists to make reusable, evidence-aware capabilities
portable across AI coding agents while preserving operator intent, provenance,
uncertainty, and human accountability.

## Roles

- **Users** install or inspect the harness and may participate in discussions.
- **Contributors** submit issues, evidence, documentation, code, or pull
  requests under the MIT License.
- **Reviewers** evaluate transferability, evidence, safety, compatibility, and
  test coverage.
- **Maintainers** triage work, make release and policy decisions, administer
  repository settings, and merge accepted changes.

The current maintainer is
[@venturemavenwill](https://github.com/venturemavenwill). Maintainers may invite
additional maintainers after sustained, constructive contributions and
demonstrated care with the project's trust and evidence boundaries.

## Decisions

Routine changes are decided through pull-request review. Maintainers prefer the
smallest reversible decision that preserves existing behavior and recorded
evidence. Significant changes to schemas, trust policy, canonical history,
licensing, governance, or compatibility should begin with a public issue or
discussion.

Maintainers seek consensus but are not required to manufacture it. When grounded
findings conflict, the project preserves the conflict and scope rather than
averaging it away. The maintainer documents the final decision and material
tradeoffs in the issue or pull request.

## Merge policy

Changes enter `main` through pull requests. Required cross-platform CI must
pass, review conversations must be resolved, history stays linear, and force
pushes and branch deletion are blocked, including for administrators. Existing
namespace manifests and claims are append-only. Squash merging keeps each
accepted improvement auditable as one integration event.

A maintainer approves every contribution they did not author. GitHub does not
let an author approve their own pull request, so while the project has one
maintainer the required approval count is zero, and that maintainer's own
changes rely on automated gates and public visibility instead of a second
approver. This is a recorded limitation of a single-maintainer project, not a
claim of independent review. The required approval count returns to one when a
second maintainer accepts write access.

Urgent security fixes may be developed privately. The maintainer publishes the
fix and an appropriately scoped advisory as soon as disclosure is safe.

## AI-assisted participation

AI tools are welcome as assistants, reviewers, and test surfaces. They do not
receive independent authority to install software, publish content, or alter the
harness. The human account submitting a contribution is accountable for:

- reviewing the complete diff and retained evidence;
- ensuring the content is safe and legally redistributable;
- disclosing material AI assistance when it helps reproduce or assess the work;
- correcting errors and responding to review.

Model consensus is review coverage, not primary evidence. Artificially
generated stars, issues, comments, or search manipulation are not accepted.

## Changes to governance

Propose governance changes through a pull request linked to a public discussion.
The maintainer announces material changes before merging when practical. The
Git history remains the record of adopted policy.
