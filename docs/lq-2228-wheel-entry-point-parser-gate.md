# LQ-2228 Wheel entry-point parser gate

- entry_points.txt is strict UTF-8 with LF line endings.
- Its sole section is console_scripts.
- Exactly 71 unique entries are required.
- Names use the bounded liquent-command form.
- Targets remain inside dotted liquent_platform modules and callables.
- Duplicate options, invalid syntax, interpolation, and foreign sections fail.
- Existing member and metadata size bounds remain mandatory.
