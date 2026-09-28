# LQ-1547 Joint engine API marker link and size contract

- Marker observation requires exactly one filesystem link.
- Empty marker state cannot represent canonical acceptance.
- Oversized or merely bounded size is insufficient.
- Size must equal encoded acceptance bytes exactly.
- Acceptance content remains independently canonical.
- Any mismatch invalidates the complete observation.
- No normalization or repair is attempted.
