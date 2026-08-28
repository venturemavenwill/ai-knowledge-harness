<!-- aikb
{
  "schema_version": 1,
  "claim_id": "spec.guard.autonomy.referenced-artifact-authorization",
  "namespace": "guard.autonomy.tool-intent",
  "version": "1.0.0",
  "expression": "When an operator authorizes an outbound action whose payload was named by reference, the displayed preview authorizes only what it displayed; the agent must separately ratify the resolved artifact identity and the delivery mechanism, because reference resolution is agent-supplied and link delivery grants durable access that outlives the message.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "an agent performs an externally visible action that carries, links, or publishes an artifact the operator identified by reference rather than by exact identifier",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "hand-authored-unmeasured",
  "provenance": {
    "producer": "hand-authored://operator",
    "producer_version": "1.0.0",
    "authored_utc": "2026-08-28",
    "derived_from": [
      {
        "source": "observed agent incident, de-identified",
        "locator": "2026-08-28: an assistant obtained explicit operator confirmation for an outbound message preview showing recipients, subject and body, then sent a share link to an agent-resolved artifact; the resolved artifact was the editable source file rather than the operator-designated published export, was stored in a third party's personal drive, and delivery auto-provisioned five durable per-person external read grants that message recall does not revoke; retained evidence is the sent item and the post-hoc permission enumeration",
        "evidence_class": "primary-result"
      },
      {
        "source": "operator correction in the same session",
        "locator": "operator rejected the artifact choice, restated the delivery mode as an attachment, and separately faulted the latency of the correction turn, which had been spent reconstructing history while the grants remained live",
        "evidence_class": "operator-authored"
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
      "kind": "extends",
      "target": "spec.guard.autonomy.tool-intent"
    }
  ],
  "retrieval": {
    "tags": [
      "artifact-resolution",
      "blast-radius",
      "confirmation",
      "containment",
      "outbound-communication",
      "sharing-permissions"
    ]
  }
}
-->

# Ratify the resolved artifact and the delivery mechanism, not only the message

> **Authority: hand-authored, unmeasured procedure derived from a single
> observed incident.** One incident establishes that the failure mode is
> reachable and shows its mechanism. It does not establish a base rate. Apply
> this as a procedure; do not cite it as a measured frequency.

The parent procedure classifies an action by effect and requires explicit
operator confirmation naming the target for anything externally visible. That is
correct and insufficient. It treats an outbound action as a single object, so a
confirmation obtained for one facet is silently spent on all of them.

## Activation

Consult this whenever a non-read action carries a payload the operator named by
reference — "this presentation", "the deck", "that report", "the build output",
"my notes" — rather than by exact identifier. It applies to mail, chat, issue and
pull request bodies, published pages, uploads, and deploys alike.

## The failure this addresses

An outbound action has at least four independently wrong-able facets:

1. **Envelope** — who receives it.
2. **Wording** — subject and body.
3. **Payload identity** — which artifact, in which format, from which location.
4. **Delivery mechanism** — copy, link, upload, or publish.

A preview that renders the envelope and the wording invites the operator to
review the envelope and the wording. Approval of that preview is routinely
carried over to facets three and four, which were never displayed. The operator
ratified a text they could read; the agent proceeded as though they had ratified
a file they never saw and a permission grant nobody mentioned.

This is a provenance delta in the parent's sense. The wording came from the
operator; the artifact came from the agent's own search over a store. The part
most likely to be wrong was the part least likely to be reviewed.

## Rule 1: a reference is not an identifier

An operator phrase denotes an artifact only relative to context the agent cannot
fully see. Resolving it is inference, and inference is tier-3 derived content
even when the agent performed it itself.

Before an externally visible action, restate the resolution in the preview:

- exact file name and extension;
- format, and whether it is a source or an export;
- owning location, and whether the operator owns it;
- last-modified or version marker when several candidates exist;
- the alternatives that were rejected, when the search returned more than one.

Two resolutions demand a halt rather than a preview. First, when the operator
earlier designated a specific variant — a published, redacted, exported, or
approved version — and the resolved artifact is not that variant. A designated
variant usually exists precisely because the other one must not circulate.
Second, when the artifact belongs to someone other than the operator, since the
operator cannot ratify a grant on a resource they do not control.

Format asymmetry carries the risk. A source file may hold speaker notes,
revision history, comments, hidden slides, embedded data, and internal
provenance that the export exists to strip. Sending the source is therefore not
a near-miss of sending the export; it is a different disclosure.

## Rule 2: the delivery mechanism sets the class

Delivery is not a formatting preference. It changes what the action does.

| Mechanism | Effect | Class |
|---|---|---|
| Attached copy | a snapshot leaves; the original's access set is unchanged | R2 |
| Share link | recipients are granted standing access to the live resource | R3 |
| Upload to a shared location | the artifact joins another access set | R3 |
| Publish | the access set becomes unbounded | R3 |

Link delivery silently performs a permission grant. Under the parent's own
classification that is shared-destructive: it is externally visible, it persists,
and it requires a recovery path. Obtaining an R2 confirmation about message text
and then executing an R3 access grant is not a ratified action.

Consequences to hold explicitly:

- **A grant outlives its message.** Recalling, deleting, or superseding the
  message does not revoke access. The two are separate objects with separate
  lifetimes.
- **A grant may be unrevocable by the operator.** If the resource sits in
  another person's store, remediation needs that owner.
- **A grant may exceed the requested mode.** An edit-scoped link where a read
  was intended widens the effect beyond the operator's goal.

When the operator names a mechanism, that name is part of the instruction, not
decoration. "Attach it" is not satisfied by a link. When no mechanism is named,
prefer the least-permanent one that meets the goal, per the parent's safer
alternative ladder.

## Rule 3: contain before reconstructing

When a mistaken outbound action is discovered, the exposure is live for as long
as the diagnosis takes. Ordering matters.

1. **Enumerate the standing effect first.** List the access the action created,
   from the environment rather than from memory.
2. **Report it before narrating.** State what persists, what does not, and who
   can revoke it.
3. **Propose containment as its own action.** Revocation is itself R3 and needs
   its own confirmation; it is not implied by "fix it".
4. **Reconstruct history afterward.** Session logs and prior context are
   diagnostics, and diagnostics do not expire.

Investigating provenance while a grant stays live inverts this order. The
incident behind this claim did exactly that, and the operator's second complaint
was latency rather than analysis.

## Rule 4: correct the operator's model of the blast radius

An operator who says "recall the message and resend the right one" has stated a
remedy scoped to the message. When the true exposure is a permission grant, that
remedy is incomplete, and executing it as given leaves the exposure in place
while creating the impression it was handled.

Say so before acting. Naming a gap between the stated remedy and the actual
effect is not a refusal of the instruction; withholding it makes the agent
complicit in a false sense of containment. The parent's fail-closed abstention
applies: state what persists, why the stated remedy does not reach it, what the
agent will do in the interim, and what work can continue.

## Preview contract

An externally visible action carrying a referenced artifact is authorized only
when the operator has seen all four facets in one place:

```text
To:        <every recipient, expanded>
Subject:   <exact>
Body:      <exact>
Artifact:  <file name> (<format>, <source|export>) from <owning location>
Delivery:  <attachment | link> -> <access this creates, and its persistence>
```

Missing rows are unratified. If any row cannot be filled from the environment,
the action is not authorized.

## Verification

| Tier | Check |
|---|---|
| 1 | A fixture exists in which an operator designates an export and the store also contains a same-named source. |
| 2 | Replay it and assert the agent surfaces the artifact identity and halts rather than resolving to the source. |
| 3 | Assert that an instruction naming attachment delivery never produces link delivery, and that link delivery is classified R3. |
| 4 | Replay a post-incident correction and assert the standing access is enumerated and reported before session history is read. |

**Falsified if:** agents following this procedure resolve referenced artifacts no
more accurately than agents that preview envelope and wording alone, or if the
added preview rows suppress enough legitimate sends that operators route outbound
work around the agent entirely.
