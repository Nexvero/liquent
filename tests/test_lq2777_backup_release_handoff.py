from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "docs" / "lq-2777-backup-release-handoff.md"
ROADMAP = ROOT / "docs" / "technical-status-and-roadmap.md"
COMPOSE_README = ROOT / "operations" / "compose" / "README.md"
OVERLAY_DOC = ROOT / "docs" / "lq-2631-opt-in-regular-backup-compose-overlay.md"


def test_backup_release_handoff_records_immutable_evidence() -> None:
    handoff = HANDOFF.read_text(encoding="utf-8")
    for evidence in (
        "30d83187fa285cf2b443768abf97387cf5c1162e",
        "36965315794",
        "36968066698",
        (
            "ghcr.io/nexvero/liquent-backup@"
            "sha256:07387c4cecbb787864f2d91c2d5336327daa3e6a5c21809558002b73831f5f54"
        ),
        "--fail-on high --only-fixed",
        "52052200",
    ):
        assert evidence in handoff


def test_backup_release_handoff_preserves_activation_boundary() -> None:
    handoff = HANDOFF.read_text(encoding="utf-8")
    assert "does not create the private object-storage bucket" in handoff
    assert "enable the\nsystemd timers" in handoff
    assert "authorize deployment" in handoff


def test_backup_release_status_no_longer_calls_runtime_unpublished() -> None:
    compose_readme = COMPOSE_README.read_text(encoding="utf-8")
    overlay_doc = OVERLAY_DOC.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "unpublished\n  regular-backup runtime" not in compose_readme
    assert "noch nicht veröffentlichte reguläre Backup-Container" not in overlay_doc
    assert "LQ-2777 backup release handoff" in roadmap
