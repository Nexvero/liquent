# LQ-2209 Wheel RECORD content binding

- Member integrity reading precedes RECORD interpretation.
- RECORD verification reuses those bounded archive members.
- Each referenced payload is read by its exact ZipInfo identity.
- Digest and size are derived independently from accepted bytes.
- Filename and dist-info validation selects the sole RECORD path.
- Required-file and entry-point checks follow successful binding.
- Direct and sdist-roundtrip wheels use the same implementation.
