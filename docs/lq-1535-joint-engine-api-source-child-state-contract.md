# LQ-1535 Joint engine API source child state contract

- Each child state corresponds to one fixed source position.
- It must identify a regular owner-private file.
- Exact mode 0600 and effective ownership are mandatory.
- Link count must remain exactly one.
- Size must be positive and within the positional limit.
- Invalid child state invalidates the complete observation.
- No partial source observation is accepted.
