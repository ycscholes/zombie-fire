# Daily rewards command design

## Goal

Provide one low-token command for the existing patrol, mail, and legion daily
reward routes, without changing the behavior of the existing individual
commands.

## Interface

Add `daily-rewards` to `zombie_click.py`:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py daily-rewards
```

The command supports `--dry-run`, `--backend`, and the global
`--mock-bounds` simulation option. The existing default counts remain intact:
three normal patrols, five patrol-ad attempts, and two legion sweeps.

## Flow and safety

The command runs, in order: `patrol-full-from-home`, `mail-claim`, and
`legion-daily-rewards`. It uses one calibrated game-window bounds value for the
entire run, so every phase targets the same verified game window. The initial
preflight must reject a non-game or invalid window before any click.

`--dry-run` produces a combined, non-clicking plan and accepts mock bounds.
On the first failure from a phase, the composite command stops immediately and
returns that failure; it must not attempt later phases on an unknown page.
Individual commands remain available and unchanged.

## Verification

Add focused unit tests for parser registration, focus eligibility, dry-run
execution with mock bounds, shared bounds behavior, phase ordering, and
fail-fast behavior. Run the script's unit suite and one mock dry-run after the
change.
