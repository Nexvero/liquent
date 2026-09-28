# LQ-1653 Post-capture joint engine API source reobservation

- Source reobservation runs after acceptance state capture.
- Captured source root and identity are reused exactly.
- The complete two-pass source observer is invoked.
- Snapshot and all stable states must remain equal.
- Registry equality is checked in the same success phase.
- Final topology validation still follows.
- No source write or retry occurs.
