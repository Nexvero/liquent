# LQ-1405 Joint engine API untrusted marker cleanup evidence

- Tests inject broader marker mode before post-write verification.
- Tests replace canonical bytes with equal-length invalid content.
- Tests inject an immediate short read from the created descriptor.
- Every injected record failure removes the untrusted marker name.
- Hardlink and metadata-change checks have direct helper evidence.
- Successful canonical readback provides the positive control.
- Focused cleanup evidence passes under strict warnings.
