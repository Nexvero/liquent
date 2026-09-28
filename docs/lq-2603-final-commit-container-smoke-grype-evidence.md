# LQ-2603 Final-commit container smoke and Grype evidence

- Local image `sha256:ea42ec6172063b0ee06afc3455801af4e0b0cc23785e95beb7f49a1179ecc8eb` was built from code commit `d273c9af6b8cb5ad62fed399821b5570beef906b`.
- The Docker builder now copies the installable `tools` package before building the wheel.
- All 71 installed console entry points load as callables inside the final image.
- The OCI revision label equals the complete source commit without truncation.
- Runtime identity is exactly `10001:10001` and the hardened read-only smoke test passed.
- Grype used the repository configuration, `only-fixed`, and a High failure cutoff.
- The scan reported one Medium finding and zero High or Critical blockers.
- Scan JSON remains local, owner-only, and outside the repository.
- The image has no release signature and was not pushed to any registry.
- Container evidence does not authorize publication, staging, or deployment.
