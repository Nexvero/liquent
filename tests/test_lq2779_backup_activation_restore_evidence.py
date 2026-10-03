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


def test_staging_functional_acceptance_records_job_artifact_and_revocation() -> None:
    evidence = EVIDENCE.read_text(encoding="utf-8")
    for value in (
        "Z8HT3-xvK41LNMhJO0PcaxFrQszabsKEWsxTortBpjM",
        "exactly one claim and one outcome",
        "1671 bytes",
        "f8f738f7f2d37d958a8cfedafebff4fa8adaba30ea0b598194c65c3d484d8ab1",
        "`research:read=true` and `research:write=false`",
        "liveness endpoint returned HTTP 200",
    ):
        assert value in evidence


def test_scheduled_confirmation_and_rollback_cleanup_are_recorded() -> None:
    evidence = EVIDENCE.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "2026-10-03T02:23:58Z" in evidence
    assert "2997744f" in evidence
    assert "repository metadata check with no errors" in evidence
    assert "backup-images.env.pre-0.1.4` was removed" in evidence
    assert "read-only follow-up automation was paused" in evidence
    assert "LQ-2779 backup activation and restore evidence" in roadmap
