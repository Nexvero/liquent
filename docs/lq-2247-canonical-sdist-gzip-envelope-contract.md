# LQ-2247 canonical sdist gzip envelope contract

- The normalized sdist has one fully specified RFC 1952 envelope.
- Magic, compression method, flags, timestamp, XFL, and OS bytes are fixed.
- XFL denotes the selected maximum-compression profile; OS is unknown-neutral.
- No filename, comment, extra field, or header checksum is admitted.
- The trailer binds the uncompressed TAR bytes by CRC32 and modulo size.
- Envelope identity is checked independently from TAR member identity.
- This contract grants no build, signing, or publication authority.
