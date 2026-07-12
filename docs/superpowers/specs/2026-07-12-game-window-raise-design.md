# Game window raise guard

## Goal

Ensure every operating command brings the specific window titled
`向僵尸开炮` to the foreground, rather than only foregrounding the containing
WeChat process.

## Design

`focus_game_window_at_start()` will locate the title-matching window, raise it
through its accessibility `AXRaise` action, with `AXMain` as a fallback, then
set the owning process frontmost. It will retain the target window's title and
bounds while doing so. If neither accessibility operation works, the original
focus error is returned instead of being misreported as a missing window.

After the focus request, the helper will read the actual front-window snapshot.
It will accept the result only when the front window's WeChat identity, title,
and bounds match the target it selected. Geometry validation stays with the
command handler so `patrol-full-from-home --fit` can calibrate a currently
small game window after it has been focused. Otherwise it raises `ClickError`
before command dispatch or any click backend runs.

## Error handling

Failure to find, raise, or verify the title-matching window is fail-closed. A
normal `微信` window in the same process is not accepted as a substitute.
Existing per-click front-window validation remains unchanged.

## Verification

Add isolated tests that mock the AppleScript output and verify the focus helper
accepts only the game window, rejects a normal WeChat front window, and keeps
the current command-dispatch focus ordering. Run syntax, unit, self-test,
mocked dry-run, and skill validation checks.
