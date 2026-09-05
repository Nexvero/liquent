# LQ-1347 Joint engine API operation boundary contract

- One immutable binding covers root, source, and acceptance identities.
- All three identities must remain stable through complete resolution.
- Root component trust and child identity trust are jointly required.
- No valid child can compensate for a rebound root path.
- No valid root can compensate for a replaced fixed child.
- Later validation resolves current facts and compares the entire binding.
- The contract adds no operation mode or alternate root.
