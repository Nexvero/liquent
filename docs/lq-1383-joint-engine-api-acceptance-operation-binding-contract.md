# LQ-1383 Joint engine API acceptance operation binding contract

- Marker load, registry inspection, and marker record share root policy.
- Each operation acquires one descriptor-hardened working root.
- Each operation completes one final visible-root identity check.
- Operation-specific child access remains relative to the working root.
- No operation receives a weaker parent-component policy.
- No successful result escapes after final root mismatch.
- Public acceptance value and codec contracts remain unchanged.
