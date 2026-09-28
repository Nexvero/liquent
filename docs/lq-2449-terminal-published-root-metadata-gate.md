# LQ-2449 Terminal published-root metadata gate

- The final output entry must remain a real directory with workspace identity.
- Its mode must be exactly 0700 and owner must remain the current user.
- The descriptor opened immediately after rename enforces the same metadata.
- A late mode drift cannot pass through unchanged device and inode values.
- Failure safely returns the same directory to its private temporary name when possible.
- Successful return follows both early and terminal root metadata checks.
