# LQ-2108 Joint engine API single value parser action

- One private action owns option multiplicity.
- First converted value is stored unchanged.
- Any second occurrence fails closed.
- Value equality does not permit repetition.
- It performs no output.
- It reuses unavailable failure.
- No public parser API is added.
