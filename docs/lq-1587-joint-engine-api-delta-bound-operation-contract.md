# LQ-1587 Joint engine API delta-bound operation contract

- Accept completion requires inner success and proven registry delta.
- Root and source states remain unchanged throughout.
- Acceptance path and identity remain unchanged.
- Final acceptance state may differ only after delta proof.
- Marker generation and source observations remain mandatory.
- Any mismatch invalidates operation success.
- Caller allow decisions remain excluded.
