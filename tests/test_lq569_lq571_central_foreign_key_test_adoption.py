from pathlib import Path


ROOT = Path(__file__).parents[1]
TESTS = ROOT / "tests"
ADOPTED = (
    "test_lq432_persistent_manifest_handoff_registry.py",
    "test_lq435_persistent_manifest_handoff_observation_append.py",
    "test_lq443_persistent_manifest_handoff_execution.py",
    "test_lq444_persistent_manifest_handoff_recovery.py",
    "test_release_authority_registry_foundation.py",
    "test_release_key_activation.py",
    "test_release_publication_artifacts.py",
    "test_release_publication_attempt.py",
    "test_release_publication_bootstrap.py",
    "test_release_publication_execution_foundation.py",
    "test_release_publication_foundation.py",
    "test_release_publication_handoff.py",
    "test_release_publication_recovery_foundation.py",
    "test_release_registry_bootstrap.py",
    "test_release_registry_projection.py",
    "test_release_signing.py",
)


def test_all_inventoried_modules_rely_on_central_foreign_key_activation() -> None:
    assert len(ADOPTED) == 16
    for name in ADOPTED:
        source = (TESTS / name).read_text()
        assert "PRAGMA foreign_keys=ON" not in source
        assert "event.listens_for" not in source
        assert "from sqlalchemy import event" not in source
        assert ", event," not in source
        assert "build_engine" in source


def test_inventory_contract_has_exact_scope_and_exclusions() -> None:
    document = (ROOT / "docs/lq-569-redundant-sqlite-foreign-key-test-listener-inventory.md").read_text()
    for value in (
        "16 Testmodule", "vier Manifest-Handoff", "sieben Release-Publication",
        "nur als Text", "ausschließlich die 16", "Produktionscode bleiben unverändert",
    ):
        assert value in document


def test_adoption_contract_preserves_test_and_runtime_boundaries() -> None:
    document = (ROOT / "docs/lq-570-central-sqlite-foreign-key-test-adoption.md").read_text()
    for value in (
        "`event.listens_for`", "keine neue Fixture", "Assertions bleiben erhalten",
        "keine Datei unter `src/`", "LQ-558-Tests bleiben unangetastet",
    ):
        assert value in document


def test_regression_record_covers_static_and_running_evidence() -> None:
    document = (ROOT / "docs/lq-571-central-sqlite-foreign-key-adoption-regression.md").read_text()
    for value in (
        "Keines der 16", "`PRAGMA foreign_keys=ON`", "265 Tests",
        "-W error::DeprecationWarning", "keine neue Produktionswirkung",
    ):
        assert value in document


def test_completion_audit_records_full_green_matrix() -> None:
    document = (ROOT / "docs/lq-572-central-sqlite-foreign-key-test-adoption-completion-audit.md").read_text()
    for value in (
        "5085 Tests", "einem erwarteten Skip",
        "105 `postgres_integration`-Tests", "5086", "269 Tests",
        "-W error::DeprecationWarning", "ohne testlokalen Listener",
        "`IntegrityError`", "68 Console Entry Points", "69 Operator-Dateien",
        "42 Migrationen", "`20260826_0042`", "kein weiterer Slice",
    ):
        assert value in document


def test_roadmap_closes_central_foreign_key_adoption_bundle() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    section = roadmap.split(
        "- LQ-572 central SQLite foreign-key test adoption completion audit:", 1
    )[1].split("\n- LQ-192", 1)[0]
    for value in (
        "5085 normalen Tests", "105 PostgreSQL-Tests", "68/69/42",
        "20260826_0042", "kein weiterer Slice",
    ):
        assert value in section
