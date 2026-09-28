from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = (
    ROOT
    / "docs/lq-2742-staging-promotion-reconciliation-settings-installation-cli-contract.md"
)


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_contract_requires_exactly_four_explicit_paths_without_discovery() -> None:
    text = _text()
    assert "exactly four explicit absolute paths" in text
    assert "provider source, provider target, process source and process target" in text
    assert "accepts exactly four positional arguments" in text
    assert "absolute, non-root path without parent traversal" in text
    assert "supplies no default path" in text
    assert "not read from environment variables" in text


def test_contract_fixes_tokens_streams_and_exit_codes() -> None:
    text = _text()
    assert "`installed` followed by one newline to stdout" in text
    assert "exits zero" in text
    assert "`present` followed by one newline to stderr" in text
    assert "exits three" in text
    assert "`unavailable` followed by one newline\n  to stderr and exits one" in text
    assert "`invalid_invocation` followed by one newline\n  to stderr and exits two" in text
    assert "exactly one fixed token on exactly one stream" in text


def test_neutral_presence_discloses_nothing_and_grants_no_authority() -> None:
    text = _text()
    assert "does not compare existing content" in text
    assert "authorize replacement" in text
    assert "No source content, endpoint, database URL, supplied path" in text
    assert "grants no promotion authority" in text
    assert "does not start reconciliation" in text


def test_implementation_and_packaging_remain_separate() -> None:
    text = _text()
    assert "adds no CLI implementation, installed entry point" in text
    assert "Implementation and packaging remain separate slices" in text
