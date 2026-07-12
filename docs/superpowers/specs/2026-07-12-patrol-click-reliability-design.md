# Patrol click reliability

## Goal

Make `patrol-full-from-home` report a click only when the selected click
backend can surface a dispatch failure, keep simulation independent of the
game window, and stop safely when an ad layout is not the calibrated one.

## Scope

- Make `system-events` the only backend selected by `auto`, because its
  AppleScript result exposes Accessibility failures to the helper. Give that
  dispatch up to 8 seconds to complete before failing closed.
- Keep `cgclick` as an explicit backend only. Persist its compiled helper at a
  stable, repository-local ignored path rather than using a new temporary
  executable identity per run.
- Add an injectable backend resolver so isolated tests can prove the default
  fail-closed policy without emitting mouse events.
- Split patrol ad closing into the calibrated top-right close attempt and a
  fail-closed error when it does not return the game to the expected window.
  The lower close coordinate remains available as an explicit, separately
  verified action, but is not blindly clicked by the full patrol routine.
- Apply `ad_reward_wait` before dismissing an ad reward. Mock dry-runs must not
  focus or locate a real game window.

## Non-goals

- Do not perform live game clicks as part of validation.
- Do not add image recognition, repeated screenshots, or broad ad interaction.
- Do not blindly retry alternate ad-close coordinates, which could activate ad
  content rather than dismiss it.

## Design

### Backend dispatch

`perform_click()` receives a backend order from a small resolver. With
`--backend auto`, that order contains only `system-events`; a failure or an
8-second timeout stops the command and is reported to the caller. `cgclick`,
Quartz, and `cliclick` remain explicit selections only, so an Accessibility
failure cannot be silently replaced by a CoreGraphics event whose delivery is
not observable. Each backend still reports a successful process/API call
rather than a game-state result; the patrol flow therefore retains its window
guard and clearly labels its final output as attempted.

The compiled CoreGraphics helper is cached at an ignored stable path beneath
the skill directory. This avoids a fresh temporary executable identity on
each command invocation while preserving the same compiled source and
fallback semantics.

### Patrol ad transition

The full patrol flow continues to click only the calibrated top-right ad
close. It then waits for the configured close and reward delays and requires
the game window to regain the expected foreground state before it dismisses a
reward. If the ad does not close or a different layout is displayed, the
foreground guard raises `ClickError`; the flow stops instead of clicking the
lower coordinate blindly.

### Simulation and tests

Commands with `--mock-bounds` plus `--dry-run` are non-operating and never
call the focus helper. Tests cover the focus classification, auto backend
policy, stable helper-cache path construction, ad reward-delay placement, and
mock dry-run dispatch. All tests use patches/mocks only.

## Acceptance criteria

1. `auto` uses only `system-events`; its 8-second timeout or any dispatch
   failure stops the command without a fallback click.
2. An explicit `--backend cgclick` run no longer creates a fresh
   `zombie-cgclick-*` directory.
3. A lower/unknown ad close layout stops the patrol flow before any lower-area
   click is issued.
4. `--mock-bounds 2,33,508,949 patrol-full-from-home --dry-run` succeeds
   without a game window.
5. Unit tests, Python compilation, skill validation, and non-clicking dry-runs
   pass.
