# LQ-1471 Joint engine API marker observation contract

- A marker observation combines decoded acceptance and file identity.
- File identity contains nonnegative device and inode facts.
- Both facts come from the same opened marker descriptor.
- Neutral marker absence remains a neutral observation result.
- Observation grants no authority beyond the recorded marker fact.
- Invalid state fails through the established detail-free boundary.
- Existing value-only marker loading remains compatible.
