# LQ-1588 Delta-bound joint engine API operation accept

- Operation composes initial inventory, one-shot, and final inventory.
- Both inventory reads share resolved registry identity.
- Exact delta is checked before outer state validation.
- Outer validator permits acceptance state change only for accept.
- Root and source state comparisons remain exact.
- Failure paths still execute final topology validation.
- Command mode remains accept-once.
