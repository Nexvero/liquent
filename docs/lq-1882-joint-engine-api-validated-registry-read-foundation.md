# LQ-1882 Joint engine API validated registry read foundation

- Registry observation and validation now form one boundary.
- Every operation consumer receives canonical evidence only.
- Shared helper prevents stage-specific validation drift.
- Result constructors still validate retained inventories.
- Identity and inventory checks remain independent.
- Existing unavailable failure remains sufficient.
- Foundation covers all operation-level registry reads.
