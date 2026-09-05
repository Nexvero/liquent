# LQ-1484 Descriptor-bound recorded marker observation

- Record retains its no-follow exclusive marker descriptor.
- Post-write verification confirms canonical bytes and stable metadata.
- File and directory synchronization complete before observation return.
- Final descriptor facts supply device and inode identity.
- Expected registry-root identity remains independently enforced.
- Pre-durable cleanup and uncertain-outcome behavior remain unchanged.
- No second path-based stat becomes the write evidence source.
