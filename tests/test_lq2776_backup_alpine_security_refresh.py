from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile.backup"
DOC = ROOT / "docs" / "lq-2776-backup-alpine-security-refresh.md"
ROADMAP = ROOT / "docs" / "technical-status-and-roadmap.md"


def test_backup_runtime_uses_the_reviewed_immutable_alpine_basis() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert (
        "postgres:18.6-alpine3.24@"
        "sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873"
        in dockerfile
    )
    runtime = dockerfile.split("FROM ${POSTGRES_IMAGE} AS runtime", 1)[1]
    assert "apt-get" not in runtime
    assert "apk add" not in runtime
    assert "--only-upgrade" not in runtime
    assert "-s /bin/false liquent-backup" in runtime
    assert "USER 10001:10001" in runtime


def test_lq2776_records_the_failed_gate_without_weakening_it() -> None:
    doc = DOC.read_text(encoding="utf-8")
    for finding in (
        "CVE-2026-84782",
        "CVE-2026-84784",
        "CVE-2026-72897",
        "CVE-2026-54873",
        "CVE-2026-103111",
    ):
        assert finding in doc
    assert "no vulnerability\nexception, gate relaxation, mutable package upgrade" in doc


def test_roadmap_contains_the_backup_alpine_handoff() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "LQ-2776 backup Alpine security refresh" in roadmap
    assert "führt in der finalen Laufzeitstufe keine Paketinstallation" in roadmap
