# LQ-2262 sdist compressed-byte identity evidence

- Tests prove canonical gzip reconstruction equals normalized bytes.
- A level-eight Deflate stream preserves the exact canonical TAR payload.
- Its canonical-looking header and valid trailer pass generic gzip reading.
- The reconstruction gate nevertheless rejects its compressed-byte drift.
- Existing tests retain envelope, TAR, manifest, and resource evidence.
- The real project sdist retains its previously recorded SHA-256 identity.
- External signing and publication evidence remain open; production_ready=false.
