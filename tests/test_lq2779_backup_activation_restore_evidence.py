from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "lq-2779-backup-activation-and-restore-evidence.md"
ROADMAP = ROOT / "docs" / "technical-status-and-roadmap.md"


def test_backup_activation_evidence_binds_release_and_snapshot() -> None:
    evidence = EVIDENCE.read_text(encoding="utf-8")
    for value in (
        "37051548122",
        "f554cbd5d39bc8c66b209148485c2b4b10dd8422",
        (
            "ghcr.io/nexvero/liquent-backup@"
            "sha256:843a7c81dcd699eb2ae475b92912885d595cf085278a6771d5218dc5a1741658"
        ),
        "52258601",
        "ca346edb",
        "eu-west-par",
    ):
        assert value in evidence


def test_restore_evidence_records_isolation_and_cleanup() -> None:
    evidence = EVIDENCE.read_text(encoding="utf-8")
    for value in (
        "159 public tables",
        "20260916_0046",
        "Liveness and readiness both returned HTTP 200",
        "internal Docker network with no published\nports",
        "were removed after acceptance",
    ):
        assert value in evidence


def test_scheduled_confirmation_and_rollback_cleanup_remain_gated() -> None:
    evidence = EVIDENCE.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert (
        "first timer-triggered backup using `0.1.4` remains intentionally pending"
        in evidence
    )
    assert "grants no authority to delete the rollback copy" in evidence
    assert "LQ-2779 backup activation and restore evidence" in roadmap
