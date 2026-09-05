# LQ-2248 sdist gzip header gate

- The local sdist verifier reads the complete compressed artifact once.
- It rejects truncated and over-limit compressed envelopes fail closed.
- It requires deflate, zero flags, and the requested SOURCE_DATE_EPOCH.
- It requires canonical XFL byte 2 and neutral OS byte 255.
- Optional gzip filename, comment, extra, and header CRC fields stay forbidden.
- Header drift is rejected before any TAR member can be accepted.
- Rejection remains detail-limited and creates no replacement artifact.
