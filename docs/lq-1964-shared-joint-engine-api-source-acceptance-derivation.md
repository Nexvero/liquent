# LQ-1964 Shared joint engine API source acceptance derivation

- One helper composes authority decoding and acceptance building.
- It returns one exact authority-acceptance pair.
- Raw decoder and builder outputs never reach operation logic.
- Source authority and envelope remain the only inputs.
- No fallback or caller-selected acceptance is available.
- Existing decoder and builder remain semantic authorities.
- No new port or persistence model is introduced.
