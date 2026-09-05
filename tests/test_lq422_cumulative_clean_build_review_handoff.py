from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-422-cumulative-clean-build-review-handoff.md"


def test_inventory_distinguishes_status_entries_from_actual_files() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "insgesamt 599 Status-Einträge" in text
    assert "insgesamt 663 uncommitted Dateien" in text
    assert "65 Pythondateien einzeln" in text
    assert "Dateizahl um 64 höher" in text


def test_handoff_records_exact_scope_and_read_only_triage() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = (
        "240 unter `docs`",
        "232 unter `tests`",
        "167 unter `src`",
        "18 unter `operations`",
        "fünf unter `tools`",
        "null Konfliktmarkerdateien",
        "null symbolische Dateien",
        "null ungetrackte Dateien größer als 1 MiB",
    )
    assert all(item in text for item in required)


def test_secret_pattern_hits_are_bounded_negative_fixtures() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "`tests/test_operational_release_bundle.py`" in text
    assert "`tests/test_lq304_research_worker_staging_evidence.py`" in text
    assert "Negativtest-Fixture" in text
    assert "kein Schlüsselbody und kein Credentialwert" in text
    assert "ersetzt keinen dedizierten Secret-Scanner" in text


def test_review_groups_do_not_claim_independent_commit_boundaries() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "sieben fachlichen Abschnitten" in text
    assert "Reviewansichten, keine unabhängigen Commitgrenzen" in text
    assert "einzelner atomarer grüner Integrationscommit" in text
    assert "vollständige Revert dieses\nCommits" in text


def test_roadmap_links_handoff_and_non_mutating_next_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(
        encoding="utf-8"
    )
    assert "- LQ-422 cumulative clean build and review handoff:" in roadmap
    assert "`docs/lq-422-cumulative-clean-build-review-handoff.md`" in roadmap
    assert "nächster Slice LQ-423 erzeugt ein deterministisches" in roadmap
