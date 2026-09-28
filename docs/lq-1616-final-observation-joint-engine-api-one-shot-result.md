# LQ-1616 Final-observation joint engine API one-shot result

- Final bound marker observation is retained in one-shot.
- It must equal the durable record observation.
- Source, marker value, time, and duration checks still follow.
- Successful return carries that exact immutable observation.
- Command-line success code remains unchanged.
- Existing direct callers remain source-compatible.
- No serialization is introduced.
