# LQ-1978 Joint engine API validated UTC foundation

- Clock read and UTC validation form one boundary.
- Exact datetime type prevents coercion semantics.
- Zero offset closes timezone interpretation.
- Shared validator prevents mode-specific drift.
- Snapshot verification receives validated instants only.
- Existing unavailable failure remains sufficient.
- Foundation covers every outer wall-clock read.
