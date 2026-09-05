# LQ-1333 Joint engine API parent rebinding evidence

- Tests rename the real parent after child capture completes.
- One case leaves the original visible parent absent.
- One case installs a symlink from the old name to the moved parent.
- One case copies identical source contents into a new real parent.
- All three cases reject across every supported layout generation.
- Unchanged parents provide positive controls.
- Focused parent-rebinding evidence passes under strict warnings.
