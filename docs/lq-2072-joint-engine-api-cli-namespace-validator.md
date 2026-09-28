# LQ-2072 Joint engine API CLI namespace validator

- One private validator owns parser handoff shape.
- It performs no parsing itself.
- It performs no clock or filesystem work.
- It returns root and mode unchanged.
- It performs no normalization.
- It reuses unavailable failure.
- No public model is added.
