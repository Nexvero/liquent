# LQ-2776: Backup Alpine security refresh

LQ-2776 moves the backup runtime from the official PostgreSQL 18.6 Trixie
image to the official PostgreSQL 18.6 Alpine 3.24 variant. PostgreSQL and
restic stay on their existing versions; only the immutable runtime basis
changes.

The controlled `0.1.3` backup release for commit
`fbcd0e3873dd58a075c80510ae1048b8432ed554` stopped before registry
authentication. The unchanged Grype gate reported the fixable High findings
`CVE-2026-84782`, `CVE-2026-84784`, `CVE-2026-72897` and `CVE-2026-54873`
against Debian OpenSSL `3.5.7-1~deb13u2`, plus `CVE-2026-103111` against
PCRE2 `10.46-1~deb13u2`. Debian identifies the corresponding `deb13u3`
packages as fixes.

The selected official runtime is fixed by patch tag and multi-platform
manifest digest:

`postgres:18.6-alpine3.24@sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873`

The Alpine PostgreSQL image already supplies the required PostgreSQL client,
Bash and certificate bundle. The Liquent runtime stage therefore performs no
package-manager installation or upgrade. It copies only the verified restic
binary and backup scripts, removes the unused privilege-transition helper,
creates the dedicated numeric runtime identity and remains non-root.

The existing backup smoke test and fixable High/Critical Grype gate remain the
authoritative acceptance boundary. This slice introduces no vulnerability
exception, gate relaxation, mutable package upgrade, publication or deployment
authority.
