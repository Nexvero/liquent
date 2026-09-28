# LQ-2536 Terminal capture-workspace gate

- Workspace metadata is measured after both terminal child observations.
- Device and inode must remain the controller-bound workspace identity.
- Exact mode 0700 and current local ownership are revalidated terminally.
- Workspace drift during child stability checks rejects the capture.
- The same open workspace descriptor anchors every parent observation.
- Descriptor cleanup follows regardless of the terminal result.
