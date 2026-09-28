from pathlib import Path


ROOT = Path(__file__).parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text()


def test_registry_and_key_process_blockers_are_now_closed():
    project = _text("pyproject.toml")
    assert 'liquent-release-signing = ' in project
    assert 'liquent-release-promotion = ' in project
    assert 'liquent-release-publication = ' in project
    for installed in (
        "liquent-release-registry-bootstrap",
        "liquent-release-key-activation",
        "liquent-release-publication-bootstrap",
        "liquent-release-publication-executor",
        "liquent-release-publication-handoff",
    ):
        assert installed in project


def test_remaining_publication_foundations_are_adapters_without_operators():
    expected_adapters = (
        "src/liquent_platform/persistence/release_publication_handoff.py",
    )
    for relative in expected_adapters:
        assert (ROOT / relative).is_file()
    present_operators = (
        "src/liquent_platform/operators/release_publication_handoff.py",
        "src/liquent_platform/operators/release_publication_executor.py",
    )
    for relative in present_operators:
        assert (ROOT / relative).is_file()


def test_runbook_does_not_claim_an_unsupported_preparation_shortcut():
    runbook = _text("operations/runbooks/release-publication-worker.md")
    assert "liquent-release-publication-handoff" in runbook
    assert "Do not proceed to the worker unless" in runbook
    assert "direct SQL" not in runbook
    assert "INSERT INTO" not in runbook
    assert "UPDATE release_" not in runbook
    assert "automatic retry" in runbook


def test_offline_release_adapters_are_not_runtime_startup_wiring():
    runtime = "\n".join((
        _text("src/liquent_platform/transport/http/app.py"),
        _text("src/liquent_platform/transport/http/main.py"),
    ))
    for module in (
        "release_registry_bootstrap",
        "release_key_activation",
        "release_publication_bootstrap",
        "release_publication_handoff",
        "release_publication",
    ):
        assert module not in runtime
