# LQ-1981 Joint engine API validated UTC evidence

- Tests reject four malformed UTC value forms.
- Exact UTC-aware datetime remains accepted.
- Accept performs three validated outer reads.
- Malformed value is rejected at each accept stage.
- Accepted audit performs two validated outer reads.
- Registry audit performs no UTC read.
- All focused warnings are treated as errors.
