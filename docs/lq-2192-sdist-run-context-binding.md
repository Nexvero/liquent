# LQ-2192 sdist run-context binding

- Successful normalization returns its verified canonical manifest.
- Distribution composition stores that manifest and derived root.
- Both facts live only in the private LocalGateContext instance.
- Failed normalization publishes neither fact to later phases.
- SOURCE_DATE_EPOCH remains the shared temporal binding.
- Wheel and sdist state remain separately represented.
- No persistence, cache, or external handoff is introduced.
