# LQ-2252 canonical sdist TAR record contract

- The normalized TAR stream is aligned to 10-KiB physical records.
- Logical member data ends on its required 512-byte block boundary.
- Exactly two logical zero blocks mark the archive end.
- Remaining bytes only complete the current physical record with zeros.
- No additional physical record is admitted after minimal completion.
- Member metadata and payload identity remain independently verified.
- The rule specifies bytes without choosing a new archive format.
