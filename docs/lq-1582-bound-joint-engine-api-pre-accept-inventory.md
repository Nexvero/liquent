# LQ-1582 Bound joint engine API pre-accept inventory

- Registry inspector supplies canonical immutable acceptance values.
- Root identity is passed unchanged from operation resolution.
- Empty registry remains a valid empty baseline.
- Unexpected names or malformed markers fail immediately.
- Inner verification begins only after baseline success.
- No registry mutation occurs during baseline capture.
- Existing duplicate precheck remains independently required.
