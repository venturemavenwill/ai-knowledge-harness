## Knowledge change

- [ ] I added new canonical records rather than editing or deleting an existing
      namespace manifest or claim.
- [ ] Any replacement claim names its predecessor in `lineage.parent_refs`.
- [ ] Any namespace metadata change is a new manifest generation with
      `supersedes`.
- [ ] Authority and evidence class are explicit; reported summaries are not
      presented as primary measurements.
- [ ] `python bin/aikb.py validate --projection` passes.
- [ ] `python -m unittest discover -s tests -v` passes.

## Verification

Describe the source retained, the checks run, and anything that remains
unverified.
