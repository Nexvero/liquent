# LQ-1378 Joint engine API acceptance root component audit

- Acceptance operations no longer follow uninspected parent symlinks.
- The held registry descriptor has one explicit operation lifetime.
- Existing marker no-follow behavior remains independently enforced.
- Read and write APIs retain their established public signatures.
- Failure cannot fall back to a resolved symlink target.
- Focused component and acceptance regression evidence passes.
- External staging evidence remains a separate readiness condition.
