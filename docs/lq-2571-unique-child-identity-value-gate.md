# LQ-2571 Unique child-identity value gate

- All validated child identity tuples must be pairwise distinct.
- Identity uniqueness is measured across the complete snapshot at once.
- Repeated device and inode values reject the entire verifier invocation.
- Valid fixed names cannot legitimize a repeated identity value.
- No namespace lookup decides whether duplicate expectations are acceptable.
- A later invocation may only use a newly supplied valid snapshot.
