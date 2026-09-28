import ast
from pathlib import Path

ROOT=Path(__file__).parents[1]
DOMAIN=ROOT/"src/liquent_platform/identity/manifest_handoff_supervisor_control_directory.py"
PORTS=ROOT/"src/liquent_platform/identity/ports.py"
def _classes(path):
    return {n.name:n for n in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(n,ast.ClassDef)}
def _methods(node): return [n.name for n in node.body if isinstance(n,ast.FunctionDef)]

def test_leaf_is_repr_free_closed_hex_material():
    text=DOMAIN.read_text(encoding="utf-8")
    assert "class ManifestHandoffSupervisorControlDirectoryLeaf" in text
    assert 're.fullmatch(r"[0-9a-f]{64}"' in text
    assert "value: str = field(repr=False)" in text

def test_state_enum_is_exactly_reserved_active_retired():
    classes=_classes(DOMAIN)
    state=classes["ManifestHandoffSupervisorControlDirectoryState"]
    assert [n.targets[0].id for n in state.body if isinstance(n,ast.Assign)] == ["RESERVED","ACTIVE","RETIRED"]

def test_transition_requests_carry_previous_closed_stage():
    text=DOMAIN.read_text(encoding="utf-8")
    assert "class ActivateManifestHandoffSupervisorControlDirectory" in text
    assert "reservation: ReservedManifestHandoffSupervisorControlDirectory" in text
    assert "class RetireManifestHandoffSupervisorControlDirectory" in text
    assert "active: ActiveManifestHandoffSupervisorControlDirectory" in text

def test_times_are_utc_and_monotone():
    text=DOMAIN.read_text(encoding="utf-8")
    assert "value.utcoffset() != timezone.utc.utcoffset(value)" in text
    assert "self.activated_at < self.reservation.reserved_at" in text
    assert "self.retired_at < self.active.activated_at" in text

def test_union_and_conflict_are_closed():
    text=DOMAIN.read_text(encoding="utf-8")
    assert "ManifestHandoffSupervisorControlDirectoryLifecycle = (" in text
    conflict=_classes(DOMAIN)["ManifestHandoffSupervisorControlDirectoryConflict"]
    assert not [n for n in conflict.body if isinstance(n,ast.AnnAssign)]

def test_store_and_lookup_ports_are_minimal():
    classes=_classes(PORTS)
    assert _methods(classes["ManifestHandoffSupervisorControlDirectoryLifecycleStore"]) == [
        "reserve_control_directory","activate_control_directory","retire_control_directory"]
    assert _methods(classes["ManifestHandoffSupervisorControlDirectoryLifecycleLookup"]) == [
        "resolve_control_directory","resolve_handle_control_directory"]

def test_no_path_authority_or_mutation_escape_hatch():
    text=DOMAIN.read_text(encoding="utf-8")
    for forbidden in ("Path","SessionPrincipal","UserId","WorkspaceId","Permission","allow","delete","cleanup","rotate"):
        assert forbidden not in text

def test_roadmap_records_lq485_and_lq486():
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-485 closed supervisor control-directory lifecycle values and ports:" in roadmap
    assert "lq-485-closed-supervisor-control-directory-lifecycle-values-and-ports.md" in roadmap
    assert "nächster Slice LQ-486" in roadmap
