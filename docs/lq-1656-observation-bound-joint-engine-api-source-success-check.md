# LQ-1656 Observation-bound joint engine API source success check

- Success check unpacks the retained source observation.
- It reopens only the resolved source root.
- Expected source identity remains mandatory.
- New observation must equal retained observation exactly.
- Content and all child states are included.
- Any unavailable read fails the whole operation.
- No normalization is performed.
