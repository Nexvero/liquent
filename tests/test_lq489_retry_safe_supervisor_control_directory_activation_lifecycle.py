import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
LIFECYCLE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_control_directory_lifecycle.py"


def _text() -> str:
    return LIFECYCLE.read_text(encoding="utf-8")


def test_lifecycle_exposes_only_ensure_active() -> None:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    methods = {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}
    assert "ensure_active" in methods
    assert not {"retire", "remove", "delete", "cleanup", "rotate"} & methods


def test_effect_order_is_reserve_create_activate() -> None:
    text = _text()
    reserve = text.index("self._registry.reserve_control_directory(request)")
    create = text.index("self._directories.create_reserved(reservation)")
    activate = text.index("self._registry.activate_control_directory(")
    assert reserve < create < activate


def test_neutral_reservation_and_conflict_stop_before_file() -> None:
    text = _text()
    reserve_section = text[text.index("reservation ="):text.index("created =")]
    assert "if reservation is None:" in reserve_section
    assert "return None" in reserve_section
    assert "type(reservation) is ManifestHandoffSupervisorControlDirectoryConflict" in reserve_section


def test_create_receives_complete_reservation_and_gates_activation() -> None:
    text = _text()
    assert "self._directories.create_reserved(reservation)" in text
    assert "type(created) is ManifestHandoffSupervisorControlDirectoryConflict" in text
    assert "if not isinstance(created, Path):" in text
    assert "ActivateManifestHandoffSupervisorControlDirectory(reservation)" in text


def test_activation_none_is_technical_not_neutral() -> None:
    text = _text()
    start = text.index("active = self._registry.activate_control_directory(")
    section = text[start:text.index("except ManifestHandoffRegistryUnavailable:", start)]
    assert "if active is None" in section
    assert "raise ManifestHandoffRegistryUnavailable" in section
    assert "return None" not in section


def test_active_must_carry_exact_reservation() -> None:
    text = _text()
    assert "type(active) is not ActiveManifestHandoffSupervisorControlDirectory" in text
    assert "if active.reservation != reservation:" in text


def test_existing_detail_free_boundary_and_no_authority_cleanup_or_wiring() -> None:
    text = _text()
    assert "ManifestHandoffRegistryUnavailable" in text
    for forbidden in (
        "SessionPrincipal", "UserId", "WorkspaceId", "Permission", "allow:",
        "os.", "mkdir", "unlink", "sqlalchemy", "create_app", "compose_",
    ):
        assert forbidden not in text


def test_roadmap_records_lq489_and_lq490() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-489 retry-safe supervisor control-directory activation lifecycle:" in roadmap
    assert "lq-489-retry-safe-supervisor-control-directory-activation-lifecycle.md" in roadmap
    assert "nächster Slice LQ-490" in roadmap
