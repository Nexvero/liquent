from pathlib import Path


ROOT = Path(__file__).parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text()


def test_all_required_offline_process_boundaries_are_installed():
    project = _text("pyproject.toml")
    commands = (
        "liquent-release-registry-bootstrap",
        "liquent-release-key-activation",
        "liquent-release-publication-bootstrap",
        "liquent-release-signing",
        "liquent-release-promotion",
        "liquent-release-publication-executor",
        "liquent-release-publication-handoff",
        "liquent-release-publication",
    )
    positions = [project.index(f"{command} =") for command in commands]
    assert len(set(positions)) == len(commands)


def test_runbook_orders_the_supported_chain_without_direct_store_shortcut():
    runbook = _text("operations/runbooks/release-publication-worker.md")
    commands = (
        "liquent-release-registry-bootstrap",
        "liquent-release-key-activation challenge",
        "liquent-release-key-activation apply",
        "liquent-release-publication-bootstrap",
        "liquent-release-signing",
        "liquent-release-promotion",
        "liquent-release-publication-executor register",
        "liquent-release-publication-handoff \\",
        "liquent-release-publication \\",
    )
    positions = [runbook.index(command) for command in commands]
    assert positions == sorted(positions)
    for shortcut in ("INSERT INTO", "UPDATE release_", "direct SQL", "Python REPL"):
        assert shortcut not in runbook


def test_handoff_output_and_retained_request_close_the_worker_bridge():
    runbook = _text("operations/runbooks/release-publication-worker.md")
    handoff = _text(
        "src/liquent_platform/operators/release_publication_handoff.py"
    )
    worker = _text("src/liquent_platform/operators/release_publication.py")
    for field in (
        "execution_id", "handoff_id", "publisher_authority_id", "channel_id",
        "channel_revision_id",
    ):
        assert field in runbook
        assert field in handoff
    assert "expected_channel_revision" in worker
    assert "accepted" in handoff
    assert "Do not proceed to the worker unless" in runbook


def test_process_bound_verifier_identity_is_consistent_and_not_request_controlled():
    runbook = _text("operations/runbooks/release-publication-worker.md")
    handoff = _text(
        "src/liquent_platform/operators/release_publication_handoff.py"
    )
    identity = "liquent-release-publication-handoff-v1"
    assert identity in runbook and identity in handoff
    request_keys = handoff[handoff.index("_json_file(path, {"):handoff.index(
        "}))", handoff.index("_json_file(path, {")
    )]
    assert "verifier" not in request_keys


def test_release_control_plane_remains_outside_http_startup_and_automation():
    runtime = "\n".join((
        _text("src/liquent_platform/transport/http/app.py"),
        _text("src/liquent_platform/transport/http/main.py"),
    ))
    for module in (
        "release_registry_bootstrap", "release_key_activation",
        "release_publication_bootstrap", "release_publication_executor",
        "release_publication_handoff", "operators.release_publication",
    ):
        assert module not in runtime
    runbook = _text("operations/runbooks/release-publication-worker.md")
    for forbidden in (
        "automatic retry", "scheduler", "deployment hook", "CI action",
        "shell loop",
    ):
        assert forbidden in runbook
