from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-425-owner-controlled-private-pre-staging-manifest-handoff-contract.md"


def test_contract_separates_generator_writer_owner_and_git_authority() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = (
        "Generator verantwortet ausschließlich die deterministischen",
        "Writer verantwortet ausschließlich die private, atomare",
        "Owner verantwortet Zielauswahl, Retention, Review",
        "Keine dieser Verantwortungen impliziert eine andere",
        "`git add`",
        "Commit oder Push",
    )
    assert all(item in text for item in required)


def test_contract_requires_private_new_non_symlink_target() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = (
        "außerhalb des\nRepository-Sourcebaums",
        "Modus `0700`",
        "Pfadkomponente frei von Symlinks",
        "Modus `0600`",
        "vorhandener Name wird niemals überschrieben",
        "nicht wiederverwendetes Suffix",
    )
    assert all(item in text for item in required)


def test_contract_freezes_atomic_no_overwrite_and_durability_order() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "temporäre Datei exklusiv" in text
    assert "Datei flushen und `fsync`" in text
    assert "ohne Overwrite atomar" in text
    assert "Zielverzeichnis `fsync`en" in text
    assert "normales Replace mit Overwrite-Semantik ist nicht zulässig" in text


def test_contract_distinguishes_neutral_unavailable_unknown_and_retention() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = (
        "`target_not_absent`",
        "`source_not_stable`",
        "`manifest_handoff_unavailable`",
        "Ausgang unbekannt",
        "keinen zweiten Write oder Bind versuchen",
        "nur an read-only Reconciliation",
        "mindestens bis zum Abschluss von Review",
        "separate owner-kontrollierte\nRetentionentscheidung",
    )
    assert all(item in text for item in required)


def test_roadmap_links_contract_and_bounded_implementation_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(
        encoding="utf-8"
    )
    assert "- LQ-425 owner-controlled private manifest handoff contract:" in roadmap
    assert "`docs/lq-425-owner-controlled-private-pre-staging-manifest-handoff-contract.md`" in roadmap
    assert "nächster Slice LQ-426 implementiert den privaten Writer" in roadmap
