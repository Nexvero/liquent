# LQ-2200 Wheel member topology gate

- Wheel paths are canonical relative POSIX names in NFC.
- Absolute, parent, empty-component, backslash, and control aliases fail.
- Member names are unique and directory records are absent.
- Every member uses deflate compression without optional flags.
- Regular files are 0644; generated RECORD is exactly 0664.
- Symlink, executable, privileged, and world-writable modes fail closed.
- Existing required-file and forbidden-name checks remain mandatory.
