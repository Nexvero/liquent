from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-491-retired-supervisor-control-directory-retention-and-cleanup-contract.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_retired_is_required_but_not_cleanup_authority() -> None:
    text = _text()
    assert "Retired ist notwendig" in text
    assert "Retired ist nicht hinreichend" in text
    assert "Reserved und Active sind niemals cleanupfähig" in text


def test_authority_and_retention_are_current_separate_and_target_bound() -> None:
    text = _text()
    assert "Aktuelle Cleanupauthority" in text
    assert "Authority ist keine Retention" in text
    assert "Directory-ID, ihren Handle" in text
    assert "Caller-supplied Allowbooleans" in text
    assert "unmittelbar vor möglicher Wirkung aktuell" in text


def test_hold_recovery_and_reference_lower_bounds_fail_closed() -> None:
    text = _text()
    for section in ("Hold-Freiheit", "Recovery-Freiheit", "Referenzuntergrenze"):
        assert section in text
    for reference in ("Journal", "Runtimebinding", "Gatebinding", "korrelierte Control-Artefakte"):
        assert reference in text


def test_registry_tombstones_survive_physical_cleanup_and_never_reuse() -> None:
    text = _text()
    assert "Registryretention" in text
    assert "dauerhaft gegen Wiederverwendung gebunden" in text
    assert "Physische Abwesenheit macht keine Identität erneut verfügbar" in text


def test_filesystem_revalidation_inventory_and_artifact_binding_are_closed() -> None:
    text = _text()
    for section in ("Privates Root", "Exaktes Leaf", "Geschlossene Inventur", "Artefaktprüfung"):
        assert section in text
    assert "Device und Inode" in text
    assert "Unbekannte Namen, Unterdirectories, Symlinks, Spezialdateien" in text


def test_future_mutation_is_ordered_nonrecursive_and_fsynced() -> None:
    text = _text()
    assert "Geordnete spätere Mutation" in text
    assert "bekannte Dateien und" in text
    assert "danach das leere Leafdirectory" in text
    assert "Parentdescriptor" in text and "synchronisieren" in text
    assert "Kein rekursives Löschen" in text
    assert "`rm -rf`" in text


def test_absence_conflict_unavailability_and_unknown_effect_are_distinct() -> None:
    text = _text()
    for section in (
        "Autoritative Abwesenheit", "Konflikt", "Technische Unverfügbarkeit",
        "Unklarer Mutationsausgang",
    ):
        assert section in text
    assert "read-only Reconciliation" in text


def test_contract_adds_no_implementation_schema_or_wiring() -> None:
    text = _text()
    assert "Keine Implementation" in text
    assert "keine Klasse, Domainwerte, Portsignatur, Tabelle, SQL" in text
    assert "Es wird keine Datei geöffnet, verändert oder entfernt" in text
    assert "Head bleibt `20260825_0034`" in text
    assert "Productioncleanup bleibt geschlossen" in text


def test_roadmap_records_lq491_and_lq492() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-491 retired supervisor control-directory retention and cleanup contract:" in roadmap
    assert "lq-491-retired-supervisor-control-directory-retention-and-cleanup-contract.md" in roadmap
    assert "nächster Slice LQ-492" in roadmap
