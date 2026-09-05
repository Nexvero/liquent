# LQ-1316 Descriptor-relative joint engine API root component walk

- One helper walks all components with directory and no-follow flags.
- Every opened descriptor is explicitly marked close-on-exec.
- The prior descriptor closes immediately after the next opens.
- The final leaf descriptor transfers to the existing source loader.
- Failure closes the currently owned descriptor before propagation.
- No string-based realpath comparison substitutes for descriptor identity.
- Existing leaf ownership and privacy checks run after traversal.
