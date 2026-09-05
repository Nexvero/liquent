# LQ-1357 Joint engine API operation child mutation evidence

- Tests cycle each child's mode from private to broader and back.
- Final private mode alone cannot hide the intervening ctime change.
- Separate tests update each child directory timestamp during resolution.
- Both mutation forms reject `source-set` and `accepted-runs`.
- Unchanged children supply the positive control.
- Earlier same-content child replacement tests remain green.
- Focused mutation evidence passes under strict warnings.
