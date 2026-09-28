# LQ-1309 Joint engine API source root replacement evidence

- Tests replace the root with a new private directory after capture.
- The replacement reproduces every canonical filename and byte value.
- All supported layout generations reject the different directory inode.
- Separate tests replace the root path with a symlink to the original.
- Non-following final metadata rejects each symlink rebinding.
- Unchanged roots provide the positive control for each generation.
- Focused replacement evidence passes under strict warnings.
