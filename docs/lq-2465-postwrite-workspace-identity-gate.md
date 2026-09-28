# LQ-2465 Postwrite workspace-identity gate

- Evidence bytes and their file descriptor are synchronized before parent completion.
- The open workspace descriptor is then synchronized and measured again.
- Its identity must match both its initial measurement and controller expectation.
- Workspace replacement during evidence creation therefore fails closed.
- Failure cleanup unlinks only the newly created relative evidence entry when reachable.
- Writer success returns only after root and file identities are jointly stable.
