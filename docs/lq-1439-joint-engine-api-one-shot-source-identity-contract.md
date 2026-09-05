# LQ-1439 Joint engine API one-shot source identity contract

- One-shot acceptance may receive an expected source-root identity.
- The same identity constrains both source reads in the operation.
- The first read establishes content only from the bound root.
- The second read cannot silently adopt a replacement root.
- Source identity remains independent from acceptance-root identity.
- Failure stays detail-free and fail-closed at the existing boundary.
- Unbound direct one-shot use remains supported.
