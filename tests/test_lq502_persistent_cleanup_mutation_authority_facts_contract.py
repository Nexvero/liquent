from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-502-persistent-cleanup-mutation-authority-facts-contract.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_four_authority_domains_are_strictly_separate_and_scoped() -> None:
    text = _text()
    for heading in (
        "## Management-Mutationsauthority", "## Hold-Mutationsauthority",
        "## Recovery-Mutationsauthority", "## Referenz-Mutationsauthority",
    ):
        assert heading in text
    assert "Keine Authority impliziert eine der anderen" in text
    assert "ausschließlich für genau einen persistenten\nManifest-Handoff-Scope" in text


def test_session_and_product_capabilities_grant_no_mutation_authority() -> None:
    text = _text()
    assert "SessionPrincipal" in text
    assert "identifiziert nur den authentifizierten Actor" in text
    assert "Cleanupmanagementfähigkeit selbst erteilt diese\nLifecycleauthority nicht" in text
    assert "keine Authority aus Membership, Research, Registry, Cleanup" in text


def test_complete_set_revisions_are_current_and_caller_cannot_supply_sets() -> None:
    text = _text()
    assert "eigene aktuelle stabile\nAuthority-Set-Revision" in text
    assert "vollständigen Satz historischer Zuordnungen" in text
    assert "Caller reichen nie einen vollständigen Authoritysatz ein" in text
    assert "exakt erwartete aktuelle\ndomänen- und scopegebundene Set-Revision" in text


def test_target_source_scope_is_derived_from_directory_and_terminal_journal() -> None:
    text = _text()
    assert "Hold-, Recovery- und Referenzcommands tragen nur eine interne Directory-ID" in text
    assert "Directory, vollständiges\nRetired-Ziel und genau ein terminales Journal ableiten" in text
    assert "Requestscope, Workspace oder Handle wird nicht akzeptiert" in text


def test_regular_lifecycle_is_closed_and_prevents_lockout() -> None:
    text = _text()
    for intent in ("Grant", "Deactivate", "Reactivate"):
        assert intent in text
    assert "kein Upsert, Delete, Transfer oder Rollenupgrade" in text
    assert "letzten aktuell wirksamen Authority-User" in text
    assert "mindestens einem anderen wirksamen Holder" in text


def test_bootstrap_is_separate_one_time_and_never_reopens() -> None:
    text = _text()
    assert "eigene kontrollierte einmalige\nBootstrapgrenze" in text
    assert "vier Bootstrapentscheidungen bleiben getrennte persistente Fakten" in text
    assert "Bootstrapgrenze dauerhaft geschlossen" in text
    assert "Migration, Appstart und Deployment erzeugen keine Bootstrapfacts" in text


def test_recovery_is_historical_scope_bound_and_does_not_change_users() -> None:
    text = _text()
    assert "historisch\nbereits autorisierten aktiven User reaktivieren" in text
    assert "keinen neuen User auswählen oder Bootstrap wiederholen" in text
    assert "Authority-Lifecycle und Recovery ändern niemals den Status eines Users" in text
    assert "eigene domänenspezifische Recovery-ID" in text


def test_revocation_blocks_later_new_mutations_but_exact_retry_is_resolvable() -> None:
    text = _text()
    assert "Authorityentzug sperrt alle später begonnenen Mutationen" in text
    assert "keinen positiven Authoritycache oder Grace-Boolean" in text
    assert "committierter exakter technischer Retry" in text
    assert "Ein neuer Intent nach Entzug bleibt gesperrt" in text


def test_no_schema_port_adapter_or_effect_is_decided() -> None:
    text = _text()
    assert "keine Domainklasse, Portsignatur, Tabelle, Migration, SQL" in text
    assert "keinen Bootstrap-, Grant-, Deactivate-, Reactivate- oder Recoverypfad" in text
    assert "`20260826_0037` und 37" in text
    assert "Der Vertrag benennt keinen neuen Exceptiontyp" in text


def test_roadmap_records_lq502_and_lq503() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-502 persistent cleanup mutation authority facts contract:" in roadmap
    assert "lq-502-persistent-cleanup-mutation-authority-facts-contract.md" in roadmap
    assert "nächster Slice LQ-503" in roadmap
