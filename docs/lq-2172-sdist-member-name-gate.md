# LQ-2172 sdist member name gate

- Tar member names are interpreted only as POSIX archive paths.
- Canonical spelling must round-trip without normalization.
- One exact name may occur at most once.
- Every accepted path shares the first observed top-level component.
- Links and special members remain rejected by normalization.
- Rejection exposes no member name or archive detail.
- Safe regular files and directories retain their payload and mode.
