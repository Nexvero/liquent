from pathlib import Path


ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "docs/lq-436-controlled-registry-to-writer-composition-contract.md"


def _text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def test_scope_binding_is_stable_and_never_caller_supplied() -> None:
    text = _text()
    required = (
        "Nicht akzeptiert werden Source- oder Zielpfad",
        "höchstens an genau eine Sourcewurzel und eine private Zielwurzel",
        "nicht aus Callerwerten, Environment-Fallback",
        "nicht auf einen anderen\nNamensraum, eine andere Source oder einen anderen Owner reassigned",
        "Umzug oder Ersatz benötigt einen neuen Scope",
    )
    assert all(value in text for value in required)


def test_reservation_start_and_writer_order_is_fail_closed() -> None:
    text = _text()
    ordered = (
        "aktive stabile Scopebinding read-only auflösen",
        "Namen über LQ-432 durable reservieren",
        "intern stabile Start-Observation-ID erzeugen",
        "`writer_started` über LQ-435 durable appendieren",
        "nur nach eindeutig bestätigtem Startappend den Writer genau einmal",
    )
    positions = [text.index(value) for value in ordered]
    assert positions == sorted(positions)
    assert "Der Writer bleibt gesperrt" in text
    assert "Konflikt, neutrales Stale oder nicht auflösbare Unverfügbarkeit" in text


def test_no_second_writer_and_crash_recovery_are_closed() -> None:
    text = _text()
    assert "darf den Writer niemals erneut aufrufen" in text
    assert "Registry enthält derzeit keinen persistenten Execution-Claim" in text
    assert "nicht allein aufgrund von Zeitablauf parallel" in text
    assert "nachdem das Ende des\nursprünglichen Prozesses" in text
    assert "keinen Timeout, Heartbeat, Claim oder Scheduler" in text


def test_writer_outcomes_and_reconciliation_are_directly_bound() -> None:
    text = _text()
    required = (
        "Nur ein direkt zurückgegebenes `manifest_handed_off`",
        "Filename muss dem registrierten Namen plus `.json` entsprechen",
        "direkt gefangener `ManifestHandoffUnknown`",
        "zuerst als\n`writer_outcome_unknown`",
        "fünf direkten Ergebnisse werden exakt auf die fünf getrennten LQ-434-",
        "Technische Reconciliation-Unverfügbarkeit erzeugt keine Observation",
    )
    assert all(value in text for value in required)


def test_roadmap_links_contract_without_composer_or_cleanup() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-436 controlled registry-to-writer composition contract:" in roadmap
    assert "`docs/lq-436-controlled-registry-to-writer-composition-contract.md`" in roadmap
    assert "nächster Slice LQ-437" in roadmap
    text = _text()
    assert "LQ-436 ergänzt keinen Domain-Typ, Port, Adapter, Resolver, Composer" in text
    assert "LQ-436 ruft\nLQ-428 nicht auf" in text
