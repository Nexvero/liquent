# LQ-2529 Capture namespace-descriptor consistency gate

- The visible child name is measured after its descriptor has been opened.
- Namespace and descriptor must have identical device and inode values.
- Each must remain a real mode-0700 directory owned by the current user.
- Same-name replacement between open and namespace measurement is rejected.
- A replacement identity is never returned or adopted into controller state.
- The existing detail-limited rejection remains the only failure result.
