# LQ-1641 Post-state-capture joint engine API inventory check

- Success check runs after operation-root state capture.
- It observes the acceptance registry again.
- Captured acceptance identity binds the observation.
- Current tuple must equal the inner final tuple exactly.
- Root and source snapshot equality already precede it.
- Final root validation still follows it.
- No write or retry occurs.
