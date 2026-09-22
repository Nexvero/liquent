# LQ-2748: Python 3.14 runtime migration

LQ-2748 moves the container runtime from Python 3.13.15 to the current stable
Python 3.14.7 slim-trixie image. The migration is limited to the immutable
builder and runtime base-image contract.

The previous Python 3.13.15 refresh removed the fixable Debian package
findings, but the Grype gate still reported fixable High-severity
`CVE-2026-82049` in the bundled CPython runtime. No patched stable Python 3.13
image is available. Python 3.14.7 contains the upstream fix and is the current
stable 3.14 patch release.

The image remains pinned by both its human-readable patch tag and the official
multi-platform manifest digest:

`python:3.14.7-slim-trixie@sha256:caaf356f40667c496d405780745b9ac25771c189a51dfcc42430d531ea09f8a2`

The package compatibility declaration remains `requires-python = ">=3.10"`.
The existing Python 3.12 CI jobs continue to protect the supported lower
runtime line; this slice does not narrow the published package contract.

No vulnerability exception, Grype relaxation, mutable package upgrade,
dependency change, application behavior change or deployment authority is
introduced. The container workflow remains the authoritative acceptance gate
for the rebuilt image.
