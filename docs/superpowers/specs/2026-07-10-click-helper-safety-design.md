# Click Helper Safety Hardening

## Scope

Harden `scripts/zombie_click.py` without changing its calibrated coordinate
model, command names, or low-token operating mode.

## Design

1. `--mock-bounds` is a simulation-only input. Any command that would issue a
   real click must reject it unless `--dry-run` is also present.
2. Before every real fixed click, re-read the frontmost window and require the
   WeChat game window titled `向僵尸开炮` with valid geometry. A mismatch aborts
   the current command before its next click; no screenshots are added.
3. All configurable waits accept only finite, non-negative values. This keeps
   the mandated randomized post-click pacing while preventing invalid sleeps.
4. Backend execution errors are normalized to `ClickError`. `auto` tries the
   remaining backends after a backend fails; explicitly selected backends fail
   cleanly with a single helper error.
5. The compiled CoreGraphics click helper uses a process-private temporary
   directory instead of predictable `/tmp` paths.

## Compatibility

Existing live commands retain their names and defaults. Existing mock dry-run
examples continue to work. A mock invocation without `--dry-run` becomes an
intentional fail-closed error.

## Verification

Run Python compilation, skill validation, self-test, mock dry-runs, and
non-clicking regression checks for rejected mock execution, negative waits,
and invalid live-window guards. No live game clicks are part of this change.
