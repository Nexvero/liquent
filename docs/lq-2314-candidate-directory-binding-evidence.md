# LQ-2314 candidate-directory binding evidence

- Tests accept an owner-controlled `0700` output directory.
- Permission drift to `0755` is rejected.
- A symlinked output-directory path is independently rejected.
- No candidate file is created through the rejected symlink.
- Existing directory-sync rollback remains residue-free.
- Existing descriptor metadata and byte checks remain intact.
- External signing and publication evidence remain open; production_ready=false.
