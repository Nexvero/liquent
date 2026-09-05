# LQ-2622 Post-merge release-candidate evidence renewal

- Candidate commit `5d62b96768eca2d56756526f2f71170ceaaeae62` contains the merged source plus the post-merge status synchronization.
- The normal clean-tree suite passed with 7167 tests and 111 explicit skips.
- The required PostgreSQL suite passed with 107 tests and 7171 deselections against PostgreSQL 16.14 with UTC sessions.
- All ten ordered controlled-preflight phases passed against the exact candidate commit.
- The canonical private receipt records `publishing_authorized=false` and `deployment_authorized=false`.
- Local image `sha256:c8868d44da48929ff559cc7964d71f9a1e9c0e33fa3f084aad5b3abab29f4513` was built from that commit.
- The image revision label equals the full candidate commit and the runtime identity is exactly `10001:10001`.
- The configured health check exists and the hardened read-only container smoke test passed.
- Grype found one Medium issue and no fixable High or Critical blocker under the repository policy.
- Scan output and controlled-preflight evidence remain owner-private below a local temporary directory.
- The image was not signed, tagged as a release, pushed, published, staged, or deployed.
- Signing still requires explicit candidate acceptance and current approved signer authority.
- Registry promotion, provider publication, staging acceptance, and deployment remain separate external gates.
