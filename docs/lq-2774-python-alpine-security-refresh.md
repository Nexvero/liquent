# LQ-2774: Python Alpine security refresh

LQ-2774 moves the application container from the official Python 3.14.7
slim-trixie image to the official Alpine 3.24 variant. Python stays on the same
stable patch release; only the immutable Linux base changes.

The previous trixie digest contains OpenSSL `3.5.7-1~deb13u2`. The unchanged
Grype gate reports fixable High-severity findings including `CVE-2026-84782`
and `CVE-2026-84784`; Debian lists `3.5.7-1~deb13u3` as the fixed trixie
package, but that package is not present in the current official Python image.

The evaluated Bookworm alternative also fails the unchanged gate. Its OpenSSL
`3.0.20-1~deb12u2` packages have fixable High and Critical findings
`CVE-2026-63076`, `CVE-2026-54874`, `CVE-2026-63072` and `CVE-2026-75803`;
the listed fix is `3.0.22-1~deb12u1`.

The selected official Alpine image is pinned by both patch tag and
multi-platform manifest digest:

`python:3.14.7-alpine3.24@sha256:9e9fde4d32eedce0b661d9ab91e826b62dddf28e928c230ec55f1866cac66b01`

The container workflow remains the authoritative acceptance gate for the
rebuilt image, including dependency installation, hardened smoke testing and
the fixable High/Critical vulnerability scan. No vulnerability exception,
Grype relaxation, mutable package upgrade, Python dependency change,
application behavior change, publication or deployment authority is
introduced.
