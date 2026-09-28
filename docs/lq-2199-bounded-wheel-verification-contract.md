# LQ-2199 Bounded wheel verification contract

- Every direct and roundtrip wheel crosses one shared bounded verifier.
- Archive bytes, member count, names, files, and total payload are limited.
- Input symlinks are never followed as release artifacts.
- Every member is read under its declared bound to trigger integrity checks.
- Limits are fixed repository policy rather than caller input.
- Bound violations fail closed before artifact acceptance.
- The contract adds no installation, publication, or execution authority.
