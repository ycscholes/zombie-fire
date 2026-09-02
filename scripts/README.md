# Script layout

`zombie_click.py` is the only CLI entry point. `zombie_common.py` owns the
shared safety boundary and input primitives, while `zombie_actions.py` owns
the calibrated action registry. Page-specific commands are split into
`zombie_tasks/{patrol,home,legion,journey,base,shop,daily}.py`.

The daily workflow has eight phases; `--from-step 7` starts at base training
hall and `--from-step 8` starts at shop training hall. Use the repository
unittest command from the root for verification.

`base-training-hall` runs the base route in order: cafeteria claim, Global
Rescue free reward, Terminal Crisis free sweep, then the existing Battlefield
Contest and Element Trial tasks. It returns to the base page when complete.
`base-training-hall-shop` starts from the already-open training hall and runs
the four requested play-shop purchases.

## Coordinate mapping

Computer Use coordinates are window-local coordinates from the game screenshot.
The `Action` registry uses the same canonical `508x949` window-local space.
CoreGraphics uses global screen coordinates, so `scale_point()` adds the
calibrated window origin once:

```text
screen_x = bounds.x + round(action.x * bounds.width / 508)
screen_y = bounds.y + round(action.y * bounds.height / 949)
```

With `bounds=(2,33,508,949)`, Computer Use `(358,513)` therefore becomes
`Action(358,513)` and CoreGraphics `(360,546)`. Do not add a title-bar offset
to the action coordinate yourself; inspect the conversion with `dry-run`.
