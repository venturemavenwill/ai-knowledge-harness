# Security policy

## Supported version

Security fixes are applied to the current `main` branch. The project does not
currently maintain older release branches.

## Report a vulnerability privately

Use GitHub's
[private vulnerability reporting form](https://github.com/venturemavenwill/ai-knowledge-harness/security/advisories/new).
Include:

- the affected commit or component;
- prerequisites and a minimal reproduction;
- the expected and observed security boundary;
- realistic impact and affected users;
- any safe mitigation you have already tested.

Do not open a public issue for an exploitable vulnerability, leaked credential,
or report that contains sensitive data. If private vulnerability reporting is
temporarily unavailable, contact the maintainer using a private contact method
listed on the
[@venturemavenwill GitHub profile](https://github.com/venturemavenwill).

## Scope

Useful reports include installer path or permission vulnerabilities, command
execution outside operator intent, path traversal, unsafe Git remote handling,
validation bypasses, and ways to mutate append-only records without detection.

Knowledge claims are untrusted reference content by design. A report should
demonstrate a boundary bypass, not only that a claim can contain imperative
prose.

This project has no bug bounty program. Reports are handled on a best-effort
basis. The maintainer will coordinate disclosure and credit with the reporter
after a fix is available.
