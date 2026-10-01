from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs/lq-2767-roadmap-status-reconciliation.md"
ROADMAP = ROOT / "docs/technical-status-and-roadmap.md"


def test_status_reconciliation_records_current_main_and_ci_boundaries() -> None:
    doc = DOC.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")

    for text in (doc, roadmap):
        assert "PR #272" in text
        assert "58f736b" in text
        assert "five executable" in text or "fünf ausführbaren" in text
        assert "provenance" in text.lower()


def test_status_reconciliation_records_immutable_runtime_basis() -> None:
    doc = DOC.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    digest = "caaf356f40667c496d405780745b9ac25771c189a51dfcc42430d531ea09f8a2"

    assert "python:3.14.7-slim-trixie" in doc
    assert digest in doc
    assert "python:3.14.7-alpine3.24" in roadmap
    assert "sha256:9e9fde4d…66b01" in roadmap
    assert "without a vulnerability exception or mutable package upgrade" in doc


def test_roadmap_records_the_selected_lq2774_alpine_basis() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")

    assert "- LQ-2774 Python Alpine security refresh:" in roadmap
    assert "`docs/lq-2774-python-alpine-security-refresh.md`" in roadmap
    assert "fixiert `alpine3.24` auf den offiziellen Manifest-Digest" in roadmap
    assert "docs/lq-2774-python-bookworm-security-refresh.md" not in roadmap


def test_status_reconciliation_preserves_inventory_and_external_boundary() -> None:
    doc = DOC.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")

    assert "76 console entry points" in doc
    assert "71 operator" in doc
    assert "46\n  linear migrations" in doc
    assert "20260916_0046" in doc
    assert "real staging\nexercise" in doc
    assert "realen autorisierten Staging-Lauf" in roadmap
    assert "grants no reconciliation, promotion or deployment\nauthority" in doc


def test_roadmap_links_lq2767_and_keeps_historical_full_suite_distinct() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")

    assert "- LQ-2767 roadmap status reconciliation:" in roadmap
    assert "`docs/lq-2767-roadmap-status-reconciliation.md`" in roadmap
    assert "**Letzter lokaler Vollteststand:** **7788 passed**, **112 skipped**" in roadmap
    assert "**Aktueller GitHub-Actions-Stand:**" in roadmap
