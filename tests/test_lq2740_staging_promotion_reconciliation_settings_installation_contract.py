from pathlib import Path


ROOT = Path(__file__).parents[1]
DOC = (
    ROOT
    / "docs/lq-2740-staging-promotion-reconciliation-settings-installation-contract.md"
)


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_contract_requires_four_explicit_paths_without_defaults() -> None:
    text = _text()
    assert "four explicit absolute paths" in text
    assert "provider source, provider\ntarget, process source and process target" in text
    assert "has no default directory" in text
    assert "absolute, non-root paths without parent traversal" in text


def test_sources_retain_exact_closed_settings_grammars() -> None:
    text = _text()
    assert "bounded to 4 KiB" in text
    assert "bounded to 8 KiB" in text
    assert "LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT=" in text
    assert "LIQUENT_STAGING_PROMOTION_RECONCILIATION_PROVIDER_SETTINGS_FILE=" in text
    assert "LIQUENT_STAGING_PROMOTION_RECONCILIATION_DATABASE_URL=" in text
    assert "does not introduce a second endpoint or\ndatabase-URL grammar" in text


def test_target_pair_is_private_bound_and_no_replace() -> None:
    text = _text()
    assert "mode `0600`" in text
    assert "exactly one hard link" in text
    assert "must be distinct and must not alias either source" in text
    assert "exact canonical provider target path" in text
    assert "No existing file is overwritten" in text
    assert "published without\nreplacement" in text
    assert "process target is the activation record" in text
    assert "complete private provider target without a process\ntarget" in text
    assert "neutral partial installation" in text


def test_contract_installs_configuration_without_authority_or_execution() -> None:
    text = _text()
    assert "conveys configuration bytes only" in text
    assert "caller has promotion authority" in text
    assert "performs no network, schema, migration or reconciliation operation" in text
    assert "adds no implementation, shell command, installed entry point" in text
    assert "Implementation remains the next separate slice" in text
