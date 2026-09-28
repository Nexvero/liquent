# LQ-1663 Joint engine API operation decision time contract

- Accept-once owns one outer decision-time interval.
- Interval begins before operation-root work.
- It ends after registry and source revalidation.
- Wall time must not move backward.
- Monotonic time must not move backward.
- Total monotonic duration may not exceed 30 seconds.
- Invalid time fails detail-free.
