# LQ-1504 State-bound joint engine API one-shot acceptance

- Record observation now includes post-sync complete marker state.
- Final observation equality consumes that state automatically.
- Temporary same-inode rewrite after record is rejected.
- Existing canonical value readback remains an additional check.
- Source revalidation and bounded decision time remain unchanged.
- Operation-root final validation remains an outer defense.
- CLI and caller authority boundaries are unchanged.
