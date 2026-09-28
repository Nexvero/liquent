# LQ-1400 Descriptor-bound joint engine API acceptance readback

- Exclusive marker creation opens one read-write no-follow descriptor.
- Existing bounded write and file synchronization complete first.
- Readback seeks that same descriptor to the first byte.
- At most canonical length plus one detection byte is read.
- Exact content and complete stable metadata are compared.
- The descriptor remains close-on-exec and locally owned.
- Directory synchronization follows successful readback only.
