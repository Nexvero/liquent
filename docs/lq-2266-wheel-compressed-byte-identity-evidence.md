# LQ-2266 wheel compressed-byte identity evidence

- Tests prove canonical reconstruction equals controlled wheel bytes.
- A low-compression rewrite retains all member payload bytes.
- Generic ZIP reading accepts that rewritten wheel without payload drift.
- The compressed-byte reconstruction gate rejects it fail closed.
- The real 422-member project wheel remains byte-identical when rebuilt.
- Existing bounded archive and source-payload evidence remains intact.
- External signing and publication evidence remain open; production_ready=false.
