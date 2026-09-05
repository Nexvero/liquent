# LQ-2488 Explicit publication-rollback outcome

- The rollback helper reports a boolean verified-restoration outcome.
- True means relative restoration, parent synchronization, and terminal checks passed.
- False covers unsafe preconditions, identity mismatch, ambiguity, or technical failure.
- The original publication rejection remains the only externally visible exception.
- Callers do not reinterpret false as permission for deletion or retry elsewhere.
- Successful forward publication never invokes the rollback outcome path.
