# Legion reward claims design

## Goal

Make `legion-reward-claims` the single owner of the foreign-challenge reward
claim flow. In this game, clicking the first visible legion reward claim button
claims all available rewards, so the flow must never click later rows.

## Flow

`legion-reward-claims` validates bounds, navigates from the legion tab to
foreign challenge, performs two free sweeps, opens the reward page, claims the
first legion reward once, switches to personal rewards, claims its first reward
once, closes the reward panel, and returns to the legion page. Each first-row
claim collects all available rewards for its tab.

`legion-daily-rewards` performs only the daily cut, then invokes
`legion-reward-claims` with its already validated bounds, backend, dry-run
state, and sweep/reward timing. This makes the reward command the sole owner of
the foreign-challenge flow.

## Interface and compatibility

The public `legion-reward-claims` command has no row-selection flags because
they imply that clicking several rows is valid when it is not. It defaults to
two sweeps. Dry-run output shows the full eight-step route.

## Safety and verification

All commands retain mock-bounds dry-runs and perform no real clicks during
tests. Focused tests will prove the exact route, including both first-row
claims, and prove that the daily command delegates after the daily cut. The
existing helper validation chain will be run before handoff.
