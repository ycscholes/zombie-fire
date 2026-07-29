# Daily Rewards Failure Recovery Design

## Goal

Increase the completion rate of `daily-rewards` without weakening its protection
against clicking an unknown page. A recoverable failure in one phase should be
reported as a partial result and should not discard already completed phases.
Window, login, geometry, and unresolved ad-state failures remain fatal.

## Current Problems

The current composite command invokes each phase directly. Any `ClickError`
escapes to `main()`, which returns exit code 2 and prevents all later phases
from running. The existing unit test explicitly locks in this fail-fast
behavior.

The helper also treats a single post-ad readiness sample as final. If the game
needs slightly longer to regain focus after an ad closes, the patrol phase and
the complete daily run fail immediately.

Finally, the current dirty worktree has the patrol handler call commented out
while retaining the `starting patrol` log line. This produces a false execution
report and breaks the phase-order test.

## Design Principles

- Preserve fail-closed behavior when the target window or page is unknown.
- Retry only failures that indicate transient delivery or transition timing.
- Continue only after a phase-specific cleanup returns the game to a known
  safe boundary.
- Keep all standalone commands and their defaults unchanged.
- Preserve the normal click pacing and the single calibrated window bounds.
- Produce an honest phase-by-phase result instead of treating a dispatched
  click as proof that a reward was claimed.

## Failure Classification

Introduce explicit error categories instead of deciding recovery from error
message strings:

- `WindowStateError`: the game window is missing, not frontmost, has changed
  geometry, or no longer matches the calibrated window. Fatal.
- `ClickDeliveryError`: the selected backend could not dispatch a click.
  Retryable once. If the retry fails, phase cleanup is attempted only when the
  window remains the calibrated game window.
- `AdReturnError`: an ad did not return to the calibrated game before the
  bounded readiness deadline. Fatal because the foreground state is unknown.
- `PhaseRecoveryError`: the original phase failed and its cleanup also failed.
  Fatal because the next phase cannot safely assume a home boundary.

Existing callers that catch `ClickError` remain compatible because the new
categories subclass it.

## Transient Retry Rules

`perform_click()` may retry the same backend once only when delivery itself
failed. Before retrying, it refocuses and revalidates the calibrated game
window, then keeps the existing randomized post-click pacing. A successful
dispatch is never repeated merely because the script cannot visually prove
that the target reacted; this avoids duplicate reward or paid actions.

The post-ad readiness check becomes bounded polling. It waits for the same
calibrated game window to become ready, using a short interval and a fixed
deadline. It does not click the lower ad-close target or probe other
coordinates. If the deadline expires, it raises `AdReturnError`.

## Phase Execution and Recovery

The composite command runs named phase definitions in this order:

1. patrol
2. calendar
3. welfare
4. mail
5. legion

Each definition contains the handler and a phase-specific recovery routine.
The runner records one of:

- `completed`: the handler returned normally.
- `recovered_failure`: the handler failed, the calibrated game window was
  still available, and cleanup completed.
- `fatal_failure`: the error was non-recoverable or cleanup failed.

Recovery is progress-aware so it does not apply a page-specific close action
before that page was entered:

| Phase | Known recovery |
| --- | --- |
| Patrol | Close the patrol panel after a failure inside the panel. An unresolved ad state remains fatal. |
| Calendar | Close the calendar after its entry click succeeded. |
| Welfare | Use the verified bottom-left back action after entry succeeded. |
| Mail | Close mail when entered, then dismiss the right-side menu; if only the menu opened, dismiss only the menu. |
| Legion | Close a known inner modal or rewards panel, then use the verified foreign-challenge back action when that page was entered. |

If the failure happens before a phase's first successful navigation click, the
phase remains at the previous safe boundary and may be recorded as recovered
without sending cleanup clicks. If cleanup succeeds, the runner continues to
the next phase. If cleanup cannot establish the expected boundary, the runner
stops.

Phase progress is tracked explicitly by the phase handler; recovery must not
infer progress from log text or exception messages.

## Result and Exit Semantics

At completion, `daily-rewards` prints one summary entry per phase, including
the original error for recovered or fatal failures.

- All phases completed: exit 0 and report `complete`.
- At least one phase had a recovered failure and later phases were attempted:
  exit 0 and report `partial`.
- A fatal failure occurred: exit 2 and report completed, recovered, skipped,
  and fatal phases.

Returning 0 for a safely recovered partial run prevents an external daily-task
runner from discarding useful completed work. The textual `partial` status
keeps the report truthful.

## Scope Boundaries

This change does not add computer vision, OCR, screenshots, paid actions,
additional ad targets, or automatic retries of clicks that were successfully
dispatched. It does not change the three quick patrols, five patrol-ad attempts,
two legion sweeps, reward-row behavior, command order, coordinates, or existing
standalone command interfaces.

The current calendar and welfare worktree changes remain in scope because they
are already part of the five-phase composite flow. Unrelated worktree changes
must not be overwritten or included in the design commit.

## Testing

Use test-driven development for each behavior:

- A delivery failure succeeds on one bounded retry.
- A dispatched click is not repeated.
- Ad readiness tolerates a delayed return within the deadline.
- Ad readiness raises `AdReturnError` after the deadline.
- A recoverable phase failure records `recovered_failure` and runs the next
  phase.
- A failed cleanup raises `PhaseRecoveryError` and prevents later phases.
- A window-state or unresolved-ad failure remains fatal.
- Patrol is executed and cannot be replaced by a log-only placeholder.
- The final summary and exit semantics distinguish `complete`, `partial`, and
  fatal runs.

Run the full unit suite, Python compilation, helper self-test, all relevant
mock dry-runs, skill validation, and `git diff --check`. Mock dry-runs validate
phase scheduling only; they do not prove live focus, page recovery, or window
fitting.
