# LQ-2521 Intermediate descriptor-cleanup failure contract

- Descriptor cleanup is part of a successful intermediate verification result.
- Failure to close any retained descriptor makes the invocation fail closed.
- A close failure cannot expose operating-system details to the caller.
- Cleanup continues after an individual child-descriptor close failure.
- The workspace descriptor still receives its own close attempt afterward.
- This technical rejection grants no release, publication, or deployment authority.
