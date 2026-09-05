# LQ-2180 sdist Unicode and mode gate

- Decomposed Unicode names are not silently normalized.
- Control, format, surrogate, and other category-C names are rejected.
- File and directory modes use one exact package-safe form each.
- Setuid, setgid, and sticky bits cannot cross the gate.
- Executable regular files are not part of this source package.
- Rejection remains independent of member spelling details.
- Existing topology and resource bounds remain mandatory.
