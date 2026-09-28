from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-530-authoritative-supervisor-cleanup-retention-policy-source-and-administration-contract.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_policy_revision_is_stable_immutable_and_data_class_bound() -> None:
    text = _text()
    assert "stabile, nichtleere, repr-freie interne ID" in text
    assert "niemals einer anderen Policydefinition" in text
    assert "Mindestaufbewahrungsdauer, Erzeugungszeit" in text
    assert "ausschließlich für\n`supervisor_control_directory`" in text


def test_minimum_retention_has_closed_positive_duration_semantics() -> None:
    text = _text()
    assert "strikt positive, begrenzte Zeitdauer" in text
    assert "eindeutiger Sekundenauflösung" in text
    assert "keine konkrete Anzahl von Tagen" in text
    assert "keine\nfachliche Defaultdauer" in text


def test_evaluation_threshold_and_clock_are_authoritative() -> None:
    text = _text()
    assert "`retired_at + minimum_retention`" in text
    assert "explizite vertrauenswürdige aware-UTC-Clock" in text
    assert "vor der Schwelle, lautet die Evaluation `retain`" in text
    assert "auf oder nach der Schwelle, lautet sie `eligible`" in text
    assert "keinen Toleranzbereich" in text


def test_active_revision_is_unique_current_and_has_no_default() -> None:
    text = _text()
    assert "höchstens eine Policyrevision aktuell\naktiv" in text
    assert "Ohne aktive Revision liefert die Policyquelle keine Evaluation" in text
    assert "keinen prozessübergreifenden positiven Cache" in text
    assert "Aktivierung, Ablösung oder Deaktivierung" in text


def test_historical_decision_requires_current_revision_for_clearance() -> None:
    text = _text()
    assert "historische `eligible`-Decision ist jedoch keine Berechtigung" in text
    assert "aktuell aktive Revision" in text
    assert "Clearanceauflösung muss die Policyrevision" in text
    assert "LQ-530 verdrahtet diese Prüfung noch nicht" in text


def test_policy_administration_authority_is_separate_and_current() -> None:
    text = _text()
    assert "eigene aktuelle\nRetention-Policy-Management-Authority-Menge" in text
    assert "SessionPrincipal` identifiziert" in text
    assert "vier LQ-525-Authority-Mengen ersetzt sie\nnicht" in text
    assert "Widerruf muss jede spätere Policymutation" in text


def test_bootstrap_lifecycle_recovery_and_activation_are_separate() -> None:
    text = _text()
    assert "separaten owner-kontrollierten Bootstrap" in text
    assert "weder Policyhistorie noch\nAuthority-Menge" in text
    assert "derselben Transaktion vollständig persistiert" in text
    assert "Recovery ist ein separater owner-kontrollierter Prozess" in text


def test_regular_administration_cannot_silently_shorten_retention() -> None:
    text = _text()
    assert "darf die aktuell aktive\nMindestaufbewahrungsdauer nicht verkürzen" in text
    assert "späteren ausdrücklich\nseparaten, höher kontrollierten Ausnahmevertrag" in text
    assert "längere aktive Revision beeinflusst jede spätere Evaluation" in text


def test_contract_opens_no_implementation_or_follow_on_effect() -> None:
    text = _text()
    assert "startet keine Retentionoperation,\nDecision, Clearance" in text
    assert "keinen Domainwert, Port, Adapter, Operator" in text
    assert "Head bleibt `20260826_0041`" in text


def test_roadmap_records_lq530_and_lq531() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-530 authoritative supervisor cleanup retention policy source and administration contract:" in roadmap
    assert "lq-530-authoritative-supervisor-cleanup-retention-policy-source-and-administration-contract.md" in roadmap
    assert "nächster Slice LQ-531" in roadmap
