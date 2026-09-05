# LQ-2318 local bundle-file evidence

- Tests seal a private regular bundle and verify its complete SHA-256.
- Published bundle mode is proven as `0600` with one filesystem link.
- A symbolic-link candidate is rejected.
- A multiply linked candidate is independently rejected.
- A lowered size ceiling proves fail-closed size enforcement.
- Existing bundle-content and candidate-digest tests remain intact.
- External signing and publication evidence remain open; production_ready=false.
