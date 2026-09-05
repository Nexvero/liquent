# LQ-2196 Private sdist wheel rebuild

- Rebuild output uses a new mode-0700 directory in the private workspace.
- The build command accepts only the bound sdist path as source.
- Exactly one liquent wheel must result.
- No dependency installation or network-enabled isolation is requested.
- The original direct wheel remains the comparison authority.
- Rebuild output is not promoted or copied to release storage.
- Command failure remains detail-limited preflight rejection.
