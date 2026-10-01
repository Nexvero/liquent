# LQ-2774: Python Bookworm security refresh

LQ-2774 moves the application container from the official Python 3.14.7
slim-trixie image to the matching official slim-bookworm variant. Python stays
on the same stable patch release; only the immutable Debian base changes.

The previous trixie digest contains OpenSSL `3.5.7-1~deb13u2`. The unchanged
Grype gate reports fixable High-severity findings including `CVE-2026-84782`
and `CVE-2026-84784`; Debian lists `3.5.7-1~deb13u3` as the fixed trixie
package, but that package is not present in the current official Python image.

The selected official Bookworm image contains OpenSSL
`3.0.20-1~deb12u2` and is pinned by both patch tag and multi-platform manifest
digest:

`python:3.14.7-slim-bookworm@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56`

The container workflow remains the authoritative acceptance gate for the
rebuilt image. No vulnerability exception, Grype relaxation, mutable package
upgrade, Python dependency change, application behavior change, publication
or deployment authority is introduced.
