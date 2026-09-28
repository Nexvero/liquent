from pathlib import Path

ROOT=Path(__file__).parents[1]
DOC=ROOT/"docs/lq-482-controlled-supervisor-production-wiring-contract.md"
def _text(): return DOC.read_text(encoding="utf-8")

def test_activation_is_explicit_complete_and_closed_by_default():
    text=_text()
    for phrase in ("Standard bleibt geschlossen","Vollständige Aktivierungsgruppe",
            "partielle Gruppe","All-or-nothing Composition"):
        assert phrase in text

def test_engine_database_control_and_capability_ownership_are_decided():
    text=_text()
    for phrase in ("Eine Datenbankengine","Engineclient-Besitz","Private Control-Root",
            "Capabilityprimitive","Outcome-Policy"):
        assert phrase in text

def test_readiness_liveness_and_shutdown_are_separate():
    text=_text()
    assert "Exakter Migrationshead" in text and "20260825_0033" in text
    assert "## Readiness" in text and "## Liveness" in text
    assert "Geordneter Shutdown" in text
    assert "nicht pauschal terminiert" in text

def test_restart_does_not_automatically_reconcile_or_cleanup():
    text=_text()
    assert "Jobs über Prozessrestart" in text
    assert "Startup reconciliiert Jobs nicht automatisch" in text
    assert "Kein Bootstrap oder Cleanup" in text

def test_no_authority_or_public_route_is_granted():
    text=_text()
    assert "Kein Authorityshortcut" in text
    assert "Production-Wiring allein fügt keine öffentliche Route hinzu" in text
    assert "SessionPrincipal identifiziert den Actor" in text

def test_slice_explicitly_has_no_implementation():
    text=_text()
    assert "## Keine Implementation" in text
    assert "ändert keine Settings, Appfactory, Entrypoint-, Compose- oder" in text

def test_roadmap_records_lq482_and_lq483():
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-482 controlled supervisor production wiring contract:" in roadmap
    assert "lq-482-controlled-supervisor-production-wiring-contract.md" in roadmap
    assert "nächster Slice LQ-483" in roadmap
