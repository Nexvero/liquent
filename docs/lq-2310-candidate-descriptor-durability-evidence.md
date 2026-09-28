# LQ-2310 candidate-descriptor durability evidence

- Tests prove published mode `0600` and link count one.
- Empty and over-limit descriptor payloads are rejected.
- Permission-mode drift is independently rejected during verification.
- A simulated directory-sync failure removes target and temporary names.
- Existing-path collision remains fail closed without overwrite.
- Existing byte and digest identity evidence remains intact.
- External signing and publication evidence remain open; production_ready=false.
