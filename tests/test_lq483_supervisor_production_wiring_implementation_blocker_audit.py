from pathlib import Path

ROOT=Path(__file__).parents[1]
DOC=ROOT/"docs/lq-483-supervisor-production-wiring-implementation-blocker-audit.md"
def _text(): return DOC.read_text(encoding="utf-8")

def test_audit_names_all_three_concrete_blockers():
    text=_text()
    assert "Blocker 1: Engineclient" in text
    assert "Blocker 2: Capabilityprimitive" in text
    assert "Blocker 3: Control-Directory-Lifecycle" in text

def test_settings_only_and_partial_activation_are_forbidden():
    text=_text()
    assert "Kein Settings-only-Erfolg" in text
    assert "Keine Teilaktivierung" in text
    assert "In-Memory-Fallback" in text

def test_runtime_and_deployment_files_remain_unchanged_by_slice():
    text=_text()
    assert "Unveränderte Settings" in text
    assert "Unveränderter Entrypoint" in text
    assert "Unveränderte Deploymentdateien" in text

def test_no_docker_socket_dummy_outcome_or_path_mapping_shortcut():
    text=_text()
    assert "DOCKER_HOST" in text
    assert "Kein Dummy-Outcome" in text
    assert "String-zu-Pfad-Abbildung" in text
    assert "kein Docker-Socket" in text

def test_safe_sequence_starts_with_control_directory():
    text=_text()
    assert "Sichere Reihenfolge" in text
    assert "Warum Control-Directory zuerst" in text
    assert "LQ-484 sollte den persistenten privaten Control-Directory-Lifecyclevertrag" in text

def test_roadmap_records_lq483_and_lq484():
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-483 supervisor production wiring implementation blocker audit:" in roadmap
    assert "lq-483-supervisor-production-wiring-implementation-blocker-audit.md" in roadmap
    assert "nächster Slice LQ-484" in roadmap
