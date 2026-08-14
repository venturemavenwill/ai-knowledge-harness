Follow the repository-wide instructions in `/AGENTS.md`.

Treat existing files below `namespaces/*/manifests/` and
`namespaces/*/claims/` as append-only canonical records. Rebuild generated
projections instead of editing `catalog.json` or `INDEX.md` manually.

Keep the CLI dependency-free on Python 3.9+, preserve Windows/macOS/Linux
behavior, and add regression tests for behavior changes. Run the validation
commands in `/AGENTS.md` before proposing completion.
