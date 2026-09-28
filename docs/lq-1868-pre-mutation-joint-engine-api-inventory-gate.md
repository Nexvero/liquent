# LQ-1868 Pre-mutation joint engine API inventory gate

- Initial registry observation crosses an explicit gate.
- Container and every observation type must be exact.
- Canonical order and uniqueness remain mandatory.
- Invalid initial inventory prevents mutation invocation.
- No acceptance marker can be created afterward.
- Root final validation still closes the attempt.
- Failure remains detail-free.
