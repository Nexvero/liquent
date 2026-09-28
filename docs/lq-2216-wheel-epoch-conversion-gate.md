# LQ-2216 Wheel epoch conversion gate

- Epoch conversion uses UTC rather than host-local timezone.
- Values before the ZIP epoch are rejected.
- Values beyond the unsigned Gzip epoch field are rejected.
- Boolean and negative aliases are not integer epoch facts.
- Odd epoch seconds round down to ZIP two-second resolution only.
- The resulting six-field tuple is compared exactly to every member.
- Conversion failure exposes no artifact or environment detail.
