# Legion reward claims design

## Goal

Make `legion-reward-claims` the single owner of the foreign-challenge reward
claim flow. In this game, clicking the first visible legion reward claim button
claims all available rewards, so the flow must never click later rows.

## Flow

`legion-reward-claims` will validate bounds, navigate from the legion tab to
foreign challenge and its left reward tab, wait for the page, click the first
claim button once, wait for the reward popup, and dismiss it with the
legion-specific dismiss coordinate.

`legion-daily-rewards` will continue to perform the daily cut and configured
foreign-challenge sweeps. It will then invoke `legion-reward-claims` with its
already validated bounds, backend, dry-run state, and reward timing. This
removes duplicate reward-page navigation and claim logic.

## Interface and compatibility

The public `legion-reward-claims` command becomes a single-claim command. Its
row-selection flags are removed because they imply that clicking several rows
is valid when it is not. Dry-run output shows only the one claim point.

## Safety and verification

All commands retain mock-bounds dry-runs and perform no real clicks during
tests. Focused tests will prove the single claim/dismiss sequence and prove
that the daily command delegates to `legion-reward-claims` after the sweeps.
The existing helper validation chain will be run before handoff.
