# LQ-2422 Distribution-directory continuity evidence

- Focused tests replace `artifacts` with a new same-named private directory.
- Explicit expected identity makes its otherwise valid two-file inventory fail closed.
- Source-order checks retain post-build and post-measurement identity checks.
- They retain cross-gate pair verification and terminal inventory binding.
- Existing digest, size, mode, link, and exact-name checks remain active.
- Production readiness remains false; publication and deployment remain forbidden.
