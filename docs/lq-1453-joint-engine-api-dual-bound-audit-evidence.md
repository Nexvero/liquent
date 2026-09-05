# LQ-1453 Joint engine API dual-bound audit evidence

- Instrumented tests observe source identity on both source reads.
- They observe acceptance identity on both marker reads.
- Existing snapshot and marker equality checks remain green.
- Exact identities preserve the established successful audit path.
- Standalone audit remains valid without outer identity binding.
- Strict warning treatment guards compatibility regressions.
- External runtime evidence remains separately required.
