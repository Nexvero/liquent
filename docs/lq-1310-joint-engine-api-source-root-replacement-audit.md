# LQ-1310 Joint engine API source root replacement audit

- Same-content replacement cannot satisfy the final identity gate.
- Symlink substitution cannot redirect final pathname validation.
- The check closes rebinding after the initial no-following open.
- Existing stable-file and stable-directory checks remain enforced.
- No new trust source or caller-selected identity exists.
- Focused replacement and compatibility tests pass.
- This audit makes no production-readiness claim.
