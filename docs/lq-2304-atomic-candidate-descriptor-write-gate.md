# LQ-2304 atomic candidate-descriptor write gate

- Descriptor bytes are fully rendered before filesystem publication.
- A private same-directory temporary file receives and syncs all bytes.
- Atomic hard-link creation publishes the completed file without overwrite.
- An existing file or symbolic link rejects fail closed.
- Failed publication removes only the private temporary file.
- No partially written target path becomes observable.
- The operation creates no external or persistent release record.
