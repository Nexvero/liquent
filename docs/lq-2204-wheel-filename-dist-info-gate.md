# LQ-2204 Wheel filename and dist-info gate

- Accepted filenames have one liquent version and exact universal tags.
- Version spelling uses bounded wheel-safe ASCII characters.
- Exactly one matching liquent-<version>.dist-info root exists.
- METADATA, WHEEL, entry_points.txt, and RECORD are mandatory there.
- Foreign or additional dist-info roots fail closed.
- Member paths cannot override the filename-derived version.
- Existing topology and resource bounds remain mandatory.
