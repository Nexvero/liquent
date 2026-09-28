# LQ-1319 Joint engine API ancestor symlink rejection contract

- A symlinked ancestor invalidates an otherwise valid source root.
- Its target contents, modes, owner, and leaf identity are irrelevant.
- Static aliases receive no compatibility exemption.
- Rejection occurs before any canonical source child is inspected.
- The rule prevents alternate path chains from inheriting root trust.
- Leaf symlink rejection remains independently required.
- Failures retain detail-free technical unavailability.
