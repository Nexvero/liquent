# LQ-2320 atomic verification-evidence publication gate

- The private output directory is created before report rendering.
- Canonical report bytes use the shared bounded atomic writer.
- A synchronized `0600` temporary file is exclusively linked into place.
- Existing report paths and symbolic links reject without overwrite.
- Directory synchronization completes before publication succeeds.
- Failure rollback remains relative to the held directory descriptor.
- No report is first exposed in the broader workspace directory.
