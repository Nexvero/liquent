# LQ-2501 Future phase-output precreation rejection

- A phase may not create a fixed directory assigned to a future phase.
- The current expected set contains only identities already captured in order.
- Precreated `bundle`, installation, roundtrip, or artifact roots fail postphase checks.
- Rejection occurs in the phase that polluted topology, not at later capture.
- The surrounding temporary workspace removes failed local output normally.
- No precreated name gains trusted identity through later phase order.
