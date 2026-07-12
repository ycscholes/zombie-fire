# CoreGraphics default click delivery

## Goal

Eliminate `system-events click timed out` from the default patrol command by
using the existing persistent CoreGraphics helper for normal click delivery.

## Decision

`--backend auto` resolves to `cgclick`. `system-events` remains an explicit
operator-selected backend for diagnosis or environments where its
Accessibility click is known to work. Quartz and `cliclick` remain explicit
alternatives and are never chosen automatically.

The persistent `.generated/zombie_cgclick` helper remains the only generated
artifact. It uses the current calibrated-window guard before every click; the
change does not relax title, foreground, geometry, ad-return, or mock-mode
safety checks.

## Error handling

If compiling or running explicit/default `cgclick` fails, the helper returns
the existing `click backend failed: cgclick: ...` form. It does not silently
switch to System Events, so the default patrol flow cannot surface the
System-Events timeout error.

## Verification

Unit tests will prove the new `auto` backend choice and explicit
System-Events behaviour. Mock patrol dry-runs, compilation, skill validation,
and diff checks remain required; no test emits a real click.
