# LQ-1351 Joint engine API operation child metadata contract

- Fixed operation children require stable metadata through resolution.
- Device and inode identity alone are necessary but not sufficient.
- Mode, owner, group, link, size, modification, and change facts are bound.
- Both `source-set` and `accepted-runs` follow the same rule.
- A transient mutation followed by apparent restoration fails closed.
- Metadata is observed from owned descriptors, not caller values.
- Rejection returns no partially trusted operation boundary.
