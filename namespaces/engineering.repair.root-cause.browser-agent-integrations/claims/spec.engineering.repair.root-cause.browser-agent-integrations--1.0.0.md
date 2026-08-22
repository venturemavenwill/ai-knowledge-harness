<!-- aikb
{
  "schema_version": 1,
  "claim_id": "spec.engineering.repair.root-cause.browser-agent-integrations",
  "namespace": "engineering.repair.root-cause.browser-agent-integrations",
  "version": "1.0.0",
  "expression": "Opaque browser-mediated agent integration failures should be localized by enabling product diagnostics first, correlating browser and backend wire evidence, and using an operator-authorized persistent CDP automation loop for repeatable one-variable experiments before changing product configuration.",
  "authority": "hand-authored",
  "scope": {
    "holds_when": "debugging an agent, plugin, connector, or tool integration whose observable symptom is mediated by a browser application",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "hand-authored-unmeasured",
  "provenance": {
    "producer": "hand-authored://operator",
    "producer_version": "1.0.0",
    "authored_utc": "2026-08-22",
    "derived_from": [
      {
        "source": "assistant-session",
        "locator": "sanitized browser-mediated agent tool failure investigation on 2026-08-22: a generic execution failure was localized to HTTP request framing, and a separate generic connector failure was localized to a policy API response; verified with developer traces, Playwright-over-CDP automation, browser network instrumentation, server wire telemetry, a same-artifact A/B replay, a mutation test, and an independent evidence audit",
        "evidence_class": "primary-result"
      },
      {
        "source": "https://github.com/gs-ai/OSINTai/tree/61e8fe7e2aab033094d7316c193adf8ec2110496",
        "locator": "v4.0.0 static design comparison: post-crawl deterministic stages, intended origin-labelled analytical records, falsifiable hypotheses, stage isolation, and omission of secret values from findings; assessment also identified model-date provenance bleed and retention of source content in raw crawl archives; no code or prose imported",
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
      "target": "engineering.repair.root-cause"
    },
    {
      "kind": "applies",
      "target": "engineering.verification.external-evidence"
    },
    {
      "kind": "applies",
      "target": "guard.autonomy.tool-intent"
    }
  ],
  "retrieval": {
    "tags": [
      "agent-integrations",
      "browser-automation",
      "browser-debugging",
      "cdp",
      "developer-mode",
      "evidence-ledger",
      "hypothesis-testing",
      "network-diagnostics",
      "playwright",
      "root-cause",
      "secret-non-retention",
      "wire-telemetry"
    ]
  }
}
-->

# Browser-mediated agent integration debugging specialization

> **Authority: hand-authored, unmeasured procedure derived from a primary
> result.** The originating investigation directly distinguished UI, policy,
> request-framing, protocol, and response-shape failures. It did not benchmark
> elapsed-time improvement across multiple projects.

Consult the parent root-cause procedure for reproduction, causal-chain, sibling
coverage, and revert-to-red requirements. This child specializes the first
localization moves for failures hidden behind a browser application.

## 1. Activation and safety boundary

Use this specialization when an agent, plugin, connector, or tool reports a
generic browser-visible failure and the causal layer is unknown. Typical
symptoms include:

- "execution unsuccessful," "something went wrong," or an empty response;
- a UI operation that appears to fail even though it may have created a
  backend resource;
- repeated consent, connection, or authentication prompts;
- uncertainty about whether the browser, gateway, or remote service sent or
  received a request.

Do not use browser automation to bypass authentication, conditional access,
data-loss prevention, role checks, consent, or another organizational policy.
A human operator authenticates the test profile and explicitly authorizes the
automation scope. Never request, read, persist, or replay their credentials.
Keep production mutations and externally visible actions behind the
confirmation level required by `guard.autonomy.tool-intent`.

Treat control of an authenticated CDP endpoint or its job queue as
credential-equivalent. Use a least-privileged test identity and non-production
environment when available. Restrict the endpoint and job files to the current
OS user, and do not expose them beyond loopback.

## 2. First-pass order

Run these steps before speculative code or configuration changes:

1. **Enable the product's developer or diagnostic mode.** Open raw debug cards,
   activity traces, correlation IDs, request IDs, status codes, and failure
   reasons. A generic UI message is a symptom, not the error record.
2. **Mark one reproduction.** Use a unique harmless marker and record UTC start,
   end, tenant or environment class, client surface, and target endpoint. Avoid
   personal or customer data in the marker.
3. **Observe every available layer.**
   - product developer trace;
   - browser DOM, console, and network;
   - management or connector API responses;
   - gateway or proxy logs;
   - application logs before parsing and before serialization.
4. **Read the actual frontend and integration code.** Inspect event handlers,
   source maps when available, API routes, generated connector metadata, and
   SDK code paths. Do not infer behavior only from rendered DOM changes.
5. **Escalate to an external real browser when the embedded browser blocks
   diagnosis.** Launch a separate, isolated, operator-authenticated browser
   profile with a loopback Chrome DevTools Protocol endpoint and connect with
   Playwright or an equivalent driver.
6. **Create a persistent experiment loop.** Submit small declarative jobs to a
   background browser worker, write structured results, inspect them, and
   course-correct. Prefer event or state conditions to fixed sleeps.

The point of this order is to buy the highest-signal evidence before spending
turns on documentation theories, repeated manual clicks, or broad source edits.

## 3. Layer-localization decision table

| Observation | First causal layer to investigate |
|---|---|
| Consent or confirmation remains visible | user authorization or orchestration gate |
| No browser/backend request exists | frontend binding, selection state, validation, policy, or stale package |
| Management API returns `4xx` | read its response body before retrying; check duplicate resources, DLP, RBAC, and validation |
| Request reaches service but JSON parsing fails | transfer framing, encoding, content type, truncation, or malformed envelope |
| Business function completes but browser drops result | response serialization, schema conformance, proxy rewriting, size limits, or client parsing |
| Request and response are valid but wrong tool fires | tool metadata, cache, routing, prompt selection, or orchestration |
| Behavior changes only after reconnect or republish | cached tool schema, connection metadata, or rollout state |

Absence of a server request is evidence. Do not patch the server for a failure
that occurred before the server boundary.

## 4. Browser instrumentation

Use the least invasive observation mechanism that exposes the missing layer:

- Playwright or DevTools request, response, console, and page-error events;
- DOM inspection for hidden dialogs, disabled controls, and developer panels;
- screenshots tied to the same reproduction marker;
- safe test-page wrappers around `fetch` and `XMLHttpRequest` to retain URL,
  method, status, and bounded failed-response bodies;
- source and source-map inspection to identify the API endpoint and state
  transition behind a control.

Install observation hooks before reproducing. Capture a baseline before
altering payloads or application behavior. Do not log authorization headers,
cookies, tokens, prompts containing sensitive data, or unbounded response
bodies.

When a UI reports failure, inspect the network response before repeating the
operation. A misleading failure can coexist with a successful create call;
blind retries then create duplicates and obscure the original defect.

## 5. Operator-authorized CDP automation pattern

When IDE-hosted browser tools cannot access a managed browser session or require
one approval per interaction:

1. Create an isolated browser profile dedicated to the test.
2. Bind its debugging endpoint to loopback on an unused port.
3. Have the operator complete sign-in and MFA directly in that browser.
4. Attach an automation client with `connectOverCDP` or the equivalent.
5. Keep authentication material inside the browser profile.
6. Give the worker a schema-validated action allowlist and an origin allowlist.
   Reject arbitrary script execution, credential access, and navigation outside
   the approved test surface by default.
7. Reconcile every job with `guard.autonomy.tool-intent`. Diagnostic reads can
   run unattended inside the approved scope; externally visible, mutating, or
   destructive actions still require their appropriate confirmation.
8. Never auto-approve arbitrary product consent. Automate only a specifically
   authorized, non-consequential test confirmation.
9. Bound the worker's lifetime, job count, output size, and accepted paths.
10. Record the target page, actions, confirmations, result text, and screenshot
    for each job.
11. Stop the worker and debugging endpoint promptly. Remove disposable profiles
    and temporary resources when their evidence-retention requirement ends and
    operator intent permits cleanup.

A minimal attachment shape is:

```javascript
const browser = await chromium.connectOverCDP(
  "http://127.0.0.1:<operator-approved-port>"
);
```

This pattern decouples diagnosis from an IDE's interaction constraints. It does
not weaken the target system's access controls.

## 6. Evidence ledger and hypothesis discipline

Keep analytical statements in separate, explicit classes:

- **observation**: directly present in a captured artifact;
- **derived result**: produced by a deterministic, repeatable check over
  observations;
- **model interpretation**: proposed by a named model and not promoted to
  evidence;
- **hypothesis**: a possible causal explanation that remains unproven;
- **next experiment**: a bounded action intended to discriminate hypotheses.

Do not merge confidence signals from different classes into one number. Source
corroboration, deterministic rule output, model self-confidence, cross-model
agreement, and human review answer different questions.

Use a stable record shape for each class:

| Record | Required fields |
|---|---|
| Observation | identifier, artifact locator, capture method, UTC time or sequence, bounded sanitized excerpt, artifact hash |
| Derived result | deterministic rule or transform, observation identifiers, output, reproducibility command |
| Model interpretation | model and version, bounded input-artifact identifiers, claim, grounding failures |
| Hypothesis | statement, support, contradiction, confirmation criterion, refutation criterion, next experiment |
| Lead | proposed action, rationale, required authority, risk, rollback, execution status |

Keep the evidence ledger append-only during an investigation. Corrections add a
new record that supersedes the mistaken interpretation; they do not rewrite the
captured observation.

For every root-cause hypothesis, record:

- supporting and contradicting observations;
- the artifacts and methods it came from;
- what observation would confirm it;
- what observation would refute it;
- the next smallest discriminating experiment.

Run deterministic checks over retained artifacts before asking a model to
synthesize causes or solutions. Evaluate model claims against the artifacts:
flag entities, errors, endpoints, or statuses that do not occur in the source,
and flag certainty language that exceeds the evidence.

Gate model-assisted conclusions on five independent dimensions rather than one
blended confidence score:

1. **Artifact grounding**: named entities, endpoints, error text, status codes,
   and sequence claims occur in cited artifacts.
2. **Claim calibration**: certainty language matches the evidence class and
   missing evidence is stated.
3. **Source traceability**: every material claim names its supporting record.
4. **Experiment discriminability**: proposed next steps predict different
   observable outcomes for competing hypotheses.
5. **Output contract**: the result contains the required evidence,
   contradiction, falsifier, risk, and residual-uncertainty fields.

A hard grounding or traceability failure prevents promotion to a root-cause
finding regardless of stronger scores elsewhere.

Stage failures should be characterized and retained without discarding evidence
from stages that can still run. Candidate next actions remain leads, not
findings, until executed.

Analyze each stage independently when possible:

1. normalize and index retained artifacts;
2. run deterministic protocol, framing, schema, timing, and policy checks;
3. correlate records across layers;
4. generate contradiction-aware hypotheses;
5. optionally request model synthesis and cross-checks;
6. evaluate model output against the artifacts;
7. produce an evidence report and next-action leads.

One failed optional stage should not erase successful captures or block
independent deterministic checks. Do not hide programming defects with a broad
catch; isolate expected stage failures into characterized error records.

Before correlating repeated errors, filter ubiquitous boilerplate such as common
framework frames, health probes, static telemetry calls, and messages present in
most runs. Common occurrence is weak causal signal unless its value, timing, or
absence changes with the defect.

When artifacts may contain credentials, retain the presence, type, location,
and count needed for diagnosis, not the secret value.

Solution candidates remain leads until tested. Each candidate names:

- the violated contract it repairs;
- the mechanism by which it should change behavior;
- the expected observable signal;
- safety and compatibility risks;
- rollback or disable path;
- the acceptance check and failure condition.

An external design comparison informed this section: OSINTai v4.0.0 at commit
`61e8fe7e2aab033094d7316c193adf8ec2110496` defines distinct observed,
derived, model, hypothesis, and lead record types; runs deterministic
post-crawl stages; and gives hypotheses explicit confirmation and refutation
criteria. The assessment also found two boundaries this specialization
deliberately tightens: model-generated dates can enter a later `DERIVED`
timeline finding without retaining model origin, and raw crawl archives can
retain source secrets even though findings omit their values. Static
assessment further found OSINTai is an HTTP crawler rather than a browser,
code-analysis, or agent-orchestration system. The assessed tag has no
`LICENSE` file despite an MIT badge. This specialization therefore retains the
repository as a pinned design reference and independently expresses the
functional methods; it imports no OSINTai source or executable dependency.

## 7. Controlled integration experiments

Build the smallest deterministic server or endpoint that returns a unique
marker. Vary one contract dimension per scenario:

- transport and HTTP framing;
- advertised and returned protocol version;
- request or response content type;
- tool definition schema;
- structured versus text result;
- authentication or connection mode.

For every run, log:

- immutable server artifact or image digest;
- startup mode and feature flags;
- allowlisted, redacted request headers;
- body byte count, hash, and a bounded sanitized preview before parsing;
- negotiated version and capability response;
- response shape, byte count, and hash immediately before serialization;
- browser-visible result and developer-mode raw trace.

Do not persist authorization, cookie, token, API-key, or credential-bearing
headers. Retain a full raw body only when it is a known non-sensitive synthetic
test payload and the operator has explicitly approved retention.

Correlate browser and server evidence by a unique marker, request ID, or narrow
UTC window. A result is not causal merely because two unrelated changes landed
before it passed.

## 8. Before/after and mutation evidence

When the defect concerns a parser, framing rule, or validation branch:

1. capture the failing browser developer trace;
2. capture the corresponding raw request or response;
3. reproduce the defect with one controlled switch on the same built artifact;
4. turn the switch off and show the same client and endpoint pass;
5. add a regression test;
6. disable or revert the repair and show the test fails again.

This separates a load-bearing repair from a coincidental clean rerun.

## 9. Anti-patterns

Avoid:

- debating documentation or protocol theory before reading the raw error;
- asking the operator to perform each repetitive browser action after an
  autonomous test profile has been authorized;
- relying only on screenshots or visible DOM text;
- using long fixed sleeps when a dialog, network event, or result file can be
  awaited;
- retrying a failed create action without reading the API response body;
- changing protocol version, transport, schema, and serializer in one test;
- declaring a remote service bug from application-level "function completed"
  telemetry without the serialized response.

## 10. Report shape

Report:

1. visible symptom and exact reproduction;
2. product developer-mode error and identifiers;
3. first layer where expected evidence diverges;
4. raw request and response facts;
5. named root cause and causal chain;
6. one-variable before/after experiment;
7. regression and mutation evidence;
8. policy or authorization blockers;
9. properties still unverified.

## Verification

A useful regression exercise presents two visually identical generic failures:
one blocked before any backend request and one caused by malformed HTTP framing
after a request reaches the server. The procedure should distinguish them in
the first diagnostic pass using developer, network, and wire evidence, without
server changes for the pre-request failure.

Periodically compare this procedure with a UI-only/manual-click baseline on
similar tasks. Record time to the first violated contract, number of operator
interventions, and number of speculative changes.

**Falsified if:** repeated correctly scoped use does not distinguish pre-request
from post-request failures more reliably than UI-only troubleshooting, does not
reduce speculative changes or operator interventions, or causes agents to
bypass access controls or retain sensitive browser data.
