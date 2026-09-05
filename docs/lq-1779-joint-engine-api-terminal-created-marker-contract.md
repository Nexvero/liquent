# LQ-1779 Joint engine API terminal created marker contract

- Success finalization retains the created marker explicitly.
- Terminal verification rereads that exact run marker.
- The reread uses the resolved acceptance-root identity.
- Complete observation equality is required.
- Replacement or state drift fails before success returns.
- The final check remains read-only and bounded.
- Failure remains detail-free.
