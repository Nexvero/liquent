# LQ-2381 Post-gate workspace-identity gate

- Immediately after each gate returns, workspace privacy and identity are measured
  again before its receipt is parsed or retained.
- A gate that changes mode, type, owner, device, or inode cannot produce an accepted
  phase receipt.
- The same identity is checked once more before final evidence construction.
- Drift rejects the run and leaves no visible success output.
- No later phase can legitimize an earlier workspace mutation.
