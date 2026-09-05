# LQ-2014 Joint engine API accept direct boundary

- Public Accept delegates to one private implementation.
- The private implementation retains all sequencing.
- Ordinary implementation failures normalize once.
- Root finalization executes before outer handling.
- Late accepted state is not rolled back.
- Successful return remains None.
- Signature remains unchanged.
