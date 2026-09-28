# LQ-1524 Converged joint engine API pre-accept source

- One-shot uses source observation before duplicate lookup.
- Observation performs both content passes and state capture.
- Mismatch raises the established unavailable result.
- Verification clocks do not authorize an unstable source.
- No acceptance record begins after capture rejection.
- Existing source identity propagation remains unchanged.
- Command-line behavior does not expand.
