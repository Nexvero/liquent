# LQ-1499 Joint engine API marker state continuity contract

- Accepted-source audit requires unchanged complete marker state.
- Same inode and restored bytes do not erase intervening mutation.
- Status-change time makes the mutation visible at final observation.
- Marker state remains independent from registry and source state.
- Both observations must remain canonical and owner-private.
- Any state mismatch fails through the detail-free boundary.
- Audit never repairs or rewrites the observed marker.
