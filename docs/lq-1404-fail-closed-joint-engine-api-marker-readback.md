# LQ-1404 Fail-closed joint engine API marker readback

- Private-mode mismatch rejects before any content trust decision.
- Content mismatch rejects even when encoded length remains unchanged.
- Premature end of readback rejects incomplete observation.
- Link-count mismatch rejects alternate hard-linked marker visibility.
- Metadata change during readback rejects unstable file state.
- Every pre-trust record rejection enters the existing cleanup path.
- No fallback load or second marker creation is attempted.
