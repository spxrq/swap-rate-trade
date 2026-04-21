# Implementation Status

Living progress tracker. Update whenever a milestone moves.

## Milestones

- [x] Repo scaffold, docs, packaging, pre-commit hook
- [ ] Lock remaining specifics of the DataFrame contract (frequency, missing-value handling, close vs mid, timezone)
- [ ] First `want/` DGP
- [ ] First `dont_want/` DGP
- [ ] Tests for first DGP pair (property-level: does each DGP actually produce what it claims?)
- [ ] First research notebook (scope TBD)

## Current focus

Scaffold in place. Next session: decide together on the first DGP pair and the remaining DataFrame-contract specifics.

## Blocked / open questions

- bQuant library allowlist not confirmed — see `BQUANT_COMPAT.md`.
- R availability in bQuant unknown — confirm with supervisor.
- DataFrame contract: frequency, missing-value convention, timezone, close-vs-mid not yet locked — see `DATA_CONTRACT.md`.
