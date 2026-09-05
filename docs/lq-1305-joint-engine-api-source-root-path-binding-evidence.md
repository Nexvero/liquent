# LQ-1305 Joint engine API source root path binding evidence

- Tests prove an unchanged visible root remains accepted.
- Tests rename the visible path away after complete child capture.
- Final revalidation rejects the now-missing path for every layout.
- Direct helper evidence rejects a different visible directory identity.
- Existing descriptor, metadata, allocation, and inventory tests remain green.
- Architecture guardrails are included in focused verification.
- Deprecation warnings are treated as test failures.
