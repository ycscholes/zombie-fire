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
