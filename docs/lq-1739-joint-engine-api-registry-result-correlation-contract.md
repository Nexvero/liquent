# LQ-1739 Joint engine API registry result correlation contract

- Registry values and observations must have equal length.
- Their canonical ordering must align exactly.
- Each observation acceptance supplies its matching value.
- Missing, extra, or reordered evidence fails construction.
- Generation state remains present only in observations.
- Value decoding remains independently retained.
- Caller correlation is never trusted.
