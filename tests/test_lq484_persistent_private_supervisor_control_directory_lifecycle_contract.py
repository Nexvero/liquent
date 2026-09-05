from pathlib import Path

ROOT=Path(__file__).parents[1]
DOC=ROOT/"docs/lq-484-persistent-private-supervisor-control-directory-lifecycle-contract.md"
def _text(): return DOC.read_text(encoding="utf-8")

def test_contract_has_closed_three_state_lifecycle():
    text=_text()
    assert "genau `reserved`, `active` und `retired`" in text
    assert "Reserved zu Active zu Retired" in text

def test_identity_leaf_and_handle_are_stable_nonreusable_facts():
    text=_text()
    assert "nicht wiederverwendbare Identität" in text
    assert "Opaques internes Leaf" in text
    assert "nicht aus Handle, Directory-ID, Claim, Owner oder Handoffname" in text

def test_durable_reserved_precedes_create_and_fsync_precedes_active():
    text=_text()
    assert text.index("Keine Datei vor Reserved") < text.index("Physische Anlage")
    assert "Active darf erst nach erfolgreicher physischer Anlage und Root-Directory-fsync" in text

def test_only_active_resolves_and_retired_does_not_delete():
    text=_text()
    assert "Nur Active darf" in text
    assert "Reserved, Retired" in text
    assert "Es löscht das physische Directory nicht" in text

def test_restart_retention_and_nonreuse_are_explicit():
    text=_text()
    for state in ("Restart RESERVED","Restart ACTIVE","Restart RETIRED"):
        assert state in text
    assert "Retention und Nichtwiederverwendung" in text
    assert "keine konkrete Aufbewahrungsdauer" in text

def test_no_path_input_authority_or_implementation():
    text=_text()
    assert "Kein Pfadinput" in text
    assert "Keine Authority" in text
    assert "Keine Implementation" in text
    assert "keine Klasse, Portsignatur, Tabelle, SQL, Migration" in text

def test_roadmap_records_lq484_and_lq485():
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-484 persistent private supervisor control-directory lifecycle contract:" in roadmap
    assert "lq-484-persistent-private-supervisor-control-directory-lifecycle-contract.md" in roadmap
    assert "nächster Slice LQ-485" in roadmap
