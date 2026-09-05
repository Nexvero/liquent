from __future__ import annotations

import os
from pathlib import Path

import pytest

import liquent_platform.operators.artifact_capability_inspect as capability
import liquent_platform.operators.artifact_probe_recovery_inspect as inspect
import liquent_platform.operators.artifact_probe_recovery_remove as remove
from liquent_platform.operators.research_worker_staging_executor import PHASES


ROOT = Path(__file__).resolve().parents[1]
TOKEN = "d" * 64


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _root(tmp_path: Path) -> Path:
    value = tmp_path / "artifacts"
    value.mkdir(mode=0o700)
    return value


def test_successful_capability_probe_cleans_and_recovery_observes_absence(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    assert capability.inspect_artifact_capabilities(TOKEN, artifact_root=root) is True
    assert inspect.classify_probe_prefix(TOKEN, artifact_root=root) == "absent"
    assert remove.remove_probe_prefix(TOKEN, artifact_root=root) == "already_absent"
    assert list(root.iterdir()) == []


def test_unknown_publish_converges_via_read_only_then_exact_remove(
    tmp_path: Path, monkeypatch,
) -> None:
    root = _root(tmp_path)
    original = capability.os.link

    def lost_acknowledgement(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("lost acknowledgement")

    monkeypatch.setattr(capability.os, "link", lost_acknowledgement)
    with pytest.raises(capability.ArtifactCapabilityInspectUnavailable):
        capability.inspect_artifact_capabilities(TOKEN, artifact_root=root)
    monkeypatch.undo()
    assert inspect.classify_probe_prefix(TOKEN, artifact_root=root) == "recoverable"
    assert remove.remove_probe_prefix(TOKEN, artifact_root=root) == "removed"
    assert inspect.classify_probe_prefix(TOKEN, artifact_root=root) == "absent"


def test_conflict_is_stable_across_inspection_and_remove(tmp_path: Path) -> None:
    root = _root(tmp_path)
    probe = root / f".liquent-staging-probe-{TOKEN}"
    probe.mkdir(mode=0o700)
    unknown = probe / "unknown"
    unknown.write_bytes(b"must-remain")
    os.chmod(unknown, 0o600)
    assert inspect.classify_probe_prefix(TOKEN, artifact_root=root) == "conflict"
    assert remove.remove_probe_prefix(TOKEN, artifact_root=root) == "conflict"
    assert unknown.read_bytes() == b"must-remain"


def test_phase_order_and_console_inventory_are_closed() -> None:
    assert PHASES.index("data_read_only") < PHASES.index("artifact_capabilities")
    assert PHASES.index("artifact_capabilities") < PHASES.index("migration_gate")
    project = _text("pyproject.toml")
    expected = {
        "liquent-artifact-capability-inspect": "artifact_capability_inspect:main",
        "liquent-artifact-probe-recovery-inspect": "artifact_probe_recovery_inspect:main",
        "liquent-artifact-probe-recovery-remove": "artifact_probe_recovery_remove:main",
        "liquent-artifact-probe-recovery": "artifact_probe_recovery:main",
        "liquent-artifact-probe-recovery-reconcile": "artifact_probe_recovery_reconcile:main",
    }
    for name, target in expected.items():
        assert f'{name} = "liquent_platform.operators.{target}"' in project


def test_reconciliation_is_structurally_read_only_for_artifact_volume() -> None:
    recovery = _text("src/liquent_platform/operators/artifact_probe_recovery.py")
    reconciliation = _text(
        "src/liquent_platform/operators/artifact_probe_recovery_reconcile.py"
    )
    assert recovery.index("artifact-probe-recovery-inspect") < recovery.index(
        "artifact-probe-recovery-remove"
    )
    assert "artifact-probe-recovery-remove" not in reconciliation
    assert "target=/var/lib/liquent/artifacts,readonly" in reconciliation
    assert "target=/var/lib/liquent/artifacts\"" not in reconciliation


def test_bundle_and_migration_claims_match_current_inventory() -> None:
    bundle = _text("tools/operational_release_bundle.py")
    assert "len(entry_points) != EXPECTED_ENTRY_POINT_COUNT" in bundle
    assert "len(operators) != EXPECTED_OPERATOR_FILE_COUNT" in bundle
    assert "len(migrations) != EXPECTED_MIGRATION_COUNT" in bundle
    assert 'details["migration_head"] != "20260826_0042"' in bundle


def test_contract_chain_and_external_blocker_remain_explicit() -> None:
    for number in range(316, 327):
        assert any((ROOT / "docs").glob(f"lq-{number}-*.md"))
    audit = " ".join(_text(
        "docs/lq-326-artifact-capability-recovery-end-to-end-audit.md"
    ).split())
    for statement in (
        "kein realer Dockercontainer", "kein gebautes autorisiertes Digest-Image",
        "kein echtes Staging-Artifactvolume", "Readiness bleibt unavailable",
    ):
        assert statement in audit
