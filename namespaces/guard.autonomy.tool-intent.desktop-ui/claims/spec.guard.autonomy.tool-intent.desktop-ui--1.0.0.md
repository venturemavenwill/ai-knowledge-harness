<!-- aikb
{
  "schema_version": 1,
  "claim_id": "spec.guard.autonomy.tool-intent.desktop-ui",
  "namespace": "guard.autonomy.tool-intent.desktop-ui",
  "version": "1.0.0",
  "expression": "An agent may act on native desktop UI on an operator's live desktop only through semantic accessibility actions that are disabled by default, admitted per application and action by an allowlist backed by a live activation probe, bound to a single-use observation lease, revalidated against element identity and an unchanged, non-target foreground window immediately before acting, serialized, never retried automatically, reported as a typed receipt, and halted by a kill switch that trips on any foreground change.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "an agent tool will perform clicks, typing, selection, toggling, expansion, or value changes in native desktop applications on a desktop a human is using; it does not govern disposable virtual machines or sandboxes that no human is using",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "hand-authored-unmeasured",
  "provenance": {
    "producer": "assistant-assessment://operator-authorized",
    "producer_version": "1.0.0",
    "authored_utc": "2026-10-08",
    "derived_from": [
      {
        "source": "operator",
        "locator": "2026-10-08 session: operator rejected a desktop automation prototype after it caused repeated involuntary window switching, and approved a gated semantic-action design for beta testing",
        "evidence_class": "operator-authored"
      },
      {
        "source": "assistant-session",
        "locator": "2026-10-08 incident: a verification loop that sent synthetic global shortcuts (Alt+Tab, Win+R) left the Windows task switcher active and alternated applications; after forced termination, modifier keys remained logically held until explicit key-up events were sent",
        "evidence_class": "primary-result"
      },
      {
        "source": "assistant-session",
        "locator": "2026-10-08 gate exercise on Windows 11 25H2: an end-to-end run performed six semantic actions on a test-owned window with no foreground change, refused lease reuse, and blocked an action under an engaged kill switch with no state change",
        "evidence_class": "primary-result"
      },
      {
        "source": "https://github.com/Hutusion/dsh-cua",
        "locator": "README and src/dsh_cua/uia.py at the 0.4.1 release: action receipts with effect_verified and foreground_changed, a cross-process mutex, and app-dependent activation notes",
        "evidence_class": "design-reference"
      },
      {
        "source": "https://github.com/trycua/cua/tree/main/libs/cua-driver",
        "locator": "rust/Skills/cua-driver/WINDOWS.md: background delivery mode that refuses rather than fronting, structured background_unavailable errors",
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
      "target": "spec.guard.autonomy.tool-intent@1.0.0"
    },
    {
      "kind": "informed-by",
      "target": "finding.desktop-ui.uia-client-activation@1.0.0"
    },
    {
      "kind": "applies",
      "target": "engineering.verification.external-evidence"
    }
  ],
  "retrieval": {
    "tags": [
      "computer-use",
      "desktop-automation",
      "foreground-window",
      "kill-switch",
      "observation-lease",
      "receipts",
      "ui-automation",
      "windows"
    ]
  }
}
-->

# Desktop UI actuation guard

## Activation

Consult this guard before an agent acts on native desktop applications on a
desktop a person is using, before adopting a computer-use tool, and immediately
after any automation run disturbs window focus or input state.

It specializes `guard.autonomy.tool-intent`. The parent's reconciliation and
blast-radius rules still apply. This claim adds desktop-specific gates.

It does not govern browser page content through a browser automation protocol,
or disposable virtual machines that no one is using.

## Why ordinary tool filtering is insufficient

Removing shell, registry, and filesystem tools and requiring a snapshot before
input does not make desktop actions safe. The unsafe part can be the input
primitive itself:

- synthetic keyboard and mouse input targets whatever window is foreground;
- global shortcuts such as task switching change system state that later steps
  depend on;
- a loop that retries focus changes can repeatedly switch applications; and
- killing an input-injecting process can leave modifier keys logically held.

"Semantic" accessibility actions are also not automatically non-activating.
See `finding.desktop-ui.uia-client-activation`.

## Procedure

### 1. Default to inspection

Expose read-only inspection first: window lists, accessibility trees, and
element search. Redact element values by default, never return password values,
and bound traversal depth and node counts. Listing an action tool must require
explicit operator opt-in.

### 2. Prohibit input-injecting and focus-changing primitives

An admitted action path must not contain:

- keyboard or mouse synthesis, pointer movement, or posted input messages;
- foreground or focus changes, window showing, or task switching;
- application launch, clipboard access, or screenshots in the same tool; or
- a focus-setting accessibility call.

Enforce this mechanically. For example, scan the action implementation's source
in tests, keep accessibility actions in one module, and fail the build when a
prohibited API appears.

### 3. Admit per application and action

Keep an allowlist that maps each application identity to the specific actions
it permits. An entry is added only after a live probe on that application shows
no foreground change for that action. Applications and frameworks differ, so a
probe on one application proves nothing about another.

### 4. Bind each action to one observation

An observation issues a single-use, short-lived lease. The lease records the
target window, its owning process, the foreground window at observation time,
and the identity of every candidate element (runtime ID, control type,
automation ID or name). Consume the lease **before** acting, so a refused or
failed action still forces re-observation.

### 5. Revalidate immediately before acting

Under a cross-process lock, refuse unless all of the following hold:

- the kill switch is not engaged;
- the action is allowlisted for this application;
- the window exists and still belongs to the leased process;
- the foreground window equals the leased foreground window;
- the target window is **not** the foreground window, because the user owns it;
- the element still matches the leased identity and is enabled; and
- for value changes, the field is not a password and not read-only.

### 6. Act once and issue a receipt

Perform exactly one accessibility pattern call. Never retry automatically.
After a short settle delay, reread the foreground window and the pattern state,
then return one of these receipts:

| Outcome | Meaning |
|---|---|
| `verified` | The pattern state changed as requested |
| `unchanged` | The call was accepted, but the state did not change |
| `unverifiable` | The action has no comparable state; re-observe to confirm |
| `failed` | The provider rejected the call |
| `refused` | A gate blocked the action; nothing was sent |
| `incident` | The foreground window changed; halt |

Never echo written values. Report only whether the field now matches.

### 7. Halt on incidents

Any foreground change trips a persistent kill switch that blocks every later
action. Only the operator releases it. The tool must not try to restore focus,
because that would require the prohibited focus primitives.

### 8. Probe safely

Run activation probes against a window the test launches and owns:

- configured never to activate and kept out of task switching;
- self-terminating after a deadline;
- one action per freshly launched window; and
- abort on the first foreground change.

Log activation messages and focus events with call stacks in the target, so a
failure reveals its trigger rather than only its symptom.

## Recovery from an input incident

If an automation run leaves the desktop switching windows or keys behaving as
if held:

1. stop sending all input and stop the automation processes;
2. send key-up events, and only key-up events, for Alt, Ctrl, Shift, Windows,
   and Tab;
3. ask the operator whether the symptom stopped; and
4. treat the tool as rejected until a redesigned path passes this guard.

## Verification

- A source scan of the action module finds no prohibited input, focus, launch,
  or clipboard API.
- A reused lease, a non-allowlisted action, a changed foreground, and an engaged
  kill switch each return `refused` with no effect on the target.
- A probe on a test-owned window shows no foreground change for every
  allowlisted action.

**Falsified if:** a tool that satisfies every gate above changes the foreground
window or input state of the operator's desktop without returning `incident`
and engaging the kill switch.
