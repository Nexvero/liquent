# LQ-2052 Composed joint engine API CLI parser policy

- Parsing precedes direct request preflight.
- Request preflight precedes clocks and I/O.
- Direct APIs remain independently closed.
- Parse failure maps to status two.
- Operation failure maps to status two.
- Success maps to status zero.
- All paths remain output-silent.
