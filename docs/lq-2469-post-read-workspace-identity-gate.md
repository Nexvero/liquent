# LQ-2469 Post-read workspace-identity gate

- The workspace descriptor remains open throughout evidence byte reading.
- After stable file verification, the parent descriptor is measured again.
- Its device and inode must match both initial and controller-bound identities.
- Workspace replacement or descriptor drift during reading fails closed.
- The returned evidence identity is trusted only after this parent recheck.
- No path reopen can silently establish a different parent as authoritative.
