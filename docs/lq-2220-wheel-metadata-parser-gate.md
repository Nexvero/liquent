# LQ-2220 Wheel metadata parser gate

- METADATA and WHEEL are LF-terminated header documents.
- Carriage-return aliases are not accepted.
- Parser defects fail before identity interpretation.
- Required singular headers occur exactly once.
- Core metadata, project name, and version remain jointly checked.
- Parsed body content cannot alter control-header identity.
- Existing member-size bounds limit both metadata documents.
