# LQ-1777 Joint engine API created delta evidence

- Tests exercise a real one-shot acceptance operation.
- Result construction derives the persisted created marker.
- Explicit caller injection of a marker is rejected.
- Immutable result assignment is rejected.
- An unrelated-only inventory fails closed.
- Existing closed-result tests remain compatible.
- No synthetic mutation path is introduced.
