# LQ-2554 Snapshotted child-identity comparison

- Initial and terminal child passes use the same snapshotted identity per name.
- Namespace and retained-descriptor observations compare against that one tuple.
- Source-mapping mutation cannot replace an expected identity mid-verification.
- No observed replacement identity is adopted into the local snapshot.
- Name-set checks also use only the snapshotted key set.
- A later invocation receives and snapshots the then-current controller state.
