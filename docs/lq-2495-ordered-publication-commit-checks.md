# LQ-2495 Ordered publication-commit checks

- Bound child verification completes before immediate namespace revalidation.
- Parent verification precedes source verification and target absence.
- Relative rename is the next namespace-changing operation after those checks.
- Forward parent synchronization still follows successful rename immediately.
- No evidence read, inventory scan, or caller callback occurs inside this ordering.
- Any precommit failure occurs before the forward rename flag is set.
