# LQ-1857 Joint engine API pre-observation value gate

- Inspection handoff is validated immediately after inspection.
- Invalid values stop before observation inventory access.
- Invalid projection cannot influence correlation work.
- Invalid projection cannot enter closed result construction.
- Root final validation still runs on failure.
- Audit remains read-only throughout rejection.
- No retry or fallback read is added.
