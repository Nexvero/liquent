# LQ-1317 Joint engine API root component evidence

- Tests prove a real component chain loads every supported layout.
- The returned descriptor has the visible leaf device and inode.
- The returned descriptor is not inheritable by a child process.
- Instrumented traversal proves all prior descriptors are closed.
- The final descriptor remains open for ownership transfer.
- Existing path-rebinding and source-stability tests remain green.
- Focused verification treats deprecation warnings as failures.
