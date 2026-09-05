# LQ-2350 Bound candidate-identity input evidence

- Focused tests prove fail-closed symbolic-link and hardlink rejection for both
  bundle and verification inputs.
- A source-boundary test proves directory-relative no-follow opening.
- It also excludes path-based byte reads and metadata reads from identity creation.
- Existing component-drift and canonical candidate-digest checks remain active.
- Production readiness remains false; publication and promotion remain separate.
