# zombie-fire-daily

`scripts/zombie_click.py` is the only CLI entry point. Shared safety, window,
scaling, timing, and click-backend code lives in `scripts/zombie_common.py`;
coordinates live in `scripts/zombie_actions.py`; tab workflows live under
`scripts/zombie_tasks/` (`patrol`, `home`, `legion`, `journey`, `base`, and
seven-phase `daily`). The entry point keeps compatibility re-exports.

Use `--mock-bounds ... --dry-run` for planning output only: mock runs do not
focus windows, click, or prove that a reward was received.
