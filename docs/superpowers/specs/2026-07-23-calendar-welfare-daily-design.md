# Calendar and Welfare Daily Reward Design

## Scope

Add safe, standalone free-reward commands for the calendar and the home-page
right-side welfare entry. Run both in the composite `daily-rewards` command.

## Safety contract

- `calendar-claim` clicks only the existing calendar entry, visible gift,
  reward dismissal, and calendar close targets.
- `welfare-claim` opens the existing welfare cluster, dismisses only the
  automatic free-reward popup, then uses the existing bottom-left back target.
- The welfare page was verified as `七日突围`; its `每日充值` and `累计充值` tabs are
  explicitly out of scope and receive no clicks.
- Each command uses the shared bound preparation, calibrated click delivery,
  normal pacing, dry-run mode, and fail-closed errors already used by mail.

## Daily composition

`daily-rewards` will retain its one-window calibration and fail-fast behavior.
The phase order becomes patrol, calendar, welfare, mail, then legion.

## Verification

Unit tests will lock down each flow's ordered click list and validate that the
composite command delegates all five phases with the shared bounds. Offline
mock dry-runs, helper self-test, Python compilation, skill validation, and
the focused unit suite will be run after the changes.
