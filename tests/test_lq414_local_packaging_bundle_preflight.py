from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-414-local-packaging-bundle-preflight.md"


def test_project_and_backend_minimums_match_the_preflight() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    audit = DOC.read_text(encoding="utf-8")
    assert 'requires = ["setuptools>=61.0"]' in project
    assert 'requires-python = ">=3.10"' in project
    assert "Python 3.9.6" in audit
    assert "Setuptools 58.0.4" in audit
    assert "vor jeder Artefakterzeugung fail-closed abgebrochen" in audit


def test_locked_ci_build_path_is_present_but_not_claimed_as_executed() -> None:
    lock = (ROOT / "requirements/ci.lock").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/quality.yml").read_text(encoding="utf-8")
    audit = DOC.read_text(encoding="utf-8")
    for requirement in (
        "build==1.5.0",
        "setuptools==80.10.2",
        "wheel==0.47.0",
    ):
        assert requirement in lock
    assert 'python-version: "3.12"' in workflow
    assert "python -m build --wheel --no-isolation" in workflow
    assert "wurde lokal aber nicht ausgeführt" in audit


def test_preflight_keeps_every_unavailable_gate_open() -> None:
    audit = DOC.read_text(encoding="utf-8")
    required = (
        "Das Modul `build` ist nicht installiert",
        "Das Modul `pytest` ist nicht installiert",
        "`LIQUENT_TEST_DATABASE_URL` ist nicht gesetzt",
        "`SOURCE_DATE_EPOCH` ist nicht gesetzt",
        "Nicht ausgeführt bedeutet ausdrücklich nicht bestanden",
        "keine neuen Artefakthashes oder Releaseprovenance",
    )
    assert all(item in audit for item in required)


def test_no_packaging_success_or_external_release_claim_is_made() -> None:
    audit = DOC.read_text(encoding="utf-8")
    assert "Der korrekte Ausgang ist deshalb `blocked before build`" in audit
    assert "LQ-414 erzeugt kein Repository-`dist/`" in audit
    assert "keine Datenbank-, Provider-, Publication-, Signatur-" in audit


def test_roadmap_links_lq414_and_the_bounded_next_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(
        encoding="utf-8"
    )
    assert "- LQ-414 local packaging and bundle preflight:" in roadmap
    assert "`docs/lq-414-local-packaging-bundle-preflight.md`" in roadmap
    assert "nächster Slice LQ-415 definiert den kontrollierten grünen" in roadmap
