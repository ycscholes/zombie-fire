# Command focus guard

## Goal

Before every command that can operate on the game window, focus the
`向僵尸开炮` window. Commands that only inspect, simulate, or describe the
helper must remain usable without an open game window.

## Scope

The command entry point will own the focus decision. A small predicate will
classify `list`, `state`, `self-test`, and `dry-run` as non-operating commands.
All other parsed subcommands will call `focus_game_window_at_start()` before
their command handler runs.

`--help` remains handled by `argparse` before command dispatch and will not
try to focus a window.

## Error handling

If focus fails, `ClickError` handling prints the existing error form and exits
with status 2. No command handler or click backend runs after a failed focus.
The existing per-click front-window validation remains unchanged as a second,
fail-closed guard against window drift.

## Verification

Run the syntax checker and internal self-test. Exercise a non-operating command
without focusing and use a mocked operating command in dry-run mode to confirm
it stays exempt. Unit-test the predicate with the operating and exempt command
names.
