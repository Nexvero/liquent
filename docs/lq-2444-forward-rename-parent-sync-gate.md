# LQ-2444 Forward-rename parent-sync gate

- Publication synchronizes the common parent descriptor immediately after rename.
- The descriptor is the same one used for source and destination relative names.
- A synchronization error is treated as publication failure, not partial success.
- The rollback gate restores the same workspace identity and synchronizes again.
- No successful path or receipt escapes before forward synchronization completes.
- Existing target-absence and no-follow parent checks remain mandatory.
