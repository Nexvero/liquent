# LQ-1447 Joint engine API expected acceptance read identity contract

- Registry reads may carry the resolved acceptance-root identity.
- The value contains exactly nonnegative device and inode facts.
- Each read compares it with the directory descriptor actually opened.
- A mismatch fails before marker content becomes audit evidence.
- Identity is a system-resolved fact, never caller authority.
- Malformed values fail closed without exposing technical detail.
- Unbound standalone reads remain supported.
