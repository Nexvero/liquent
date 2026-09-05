from pathlib import Path


ROOT = Path(__file__).parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text()


def test_supervised_release_publication_chain_has_all_internal_commands():
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
    for command in commands:
        assert f"{command} =" in project


def test_current_runbooks_keep_internal_readiness_and_environment_approval_separate():
    publication = _text("operations/runbooks/release-publication-worker.md")
    readiness = _text("operations/runbooks/release-environment-readiness.md")
    assert "Do not proceed to the worker unless" in publication
    assert "Only `approved` permits a separately supervised invocation" in readiness
    assert "It does not start that invocation" in readiness
    assert "Production test upload for this checklist" in readiness


def test_release_commands_are_not_automatic_runtime_or_ci_wiring():
    joined = "\n".join((
        _text("src/liquent_platform/transport/http/app.py"),
        _text("src/liquent_platform/transport/http/main.py"),
        _text("operations/compose/compose.yaml"),
    ))
    for command in (
        "liquent-release-registry-bootstrap",
        "liquent-release-key-activation",
        "liquent-release-publication-bootstrap",
        "liquent-release-publication-executor",
        "liquent-release-publication-handoff",
        "liquent-release-publication ",
    ):
        assert command not in joined
    workflows = "\n".join(
        path.read_text() for path in (ROOT / ".github/workflows").glob("*.yml")
    )
    assert "liquent-release-publication" not in workflows


def test_migration_and_operational_bundle_claims_match_enforced_gates():
    migration_test = _text("tests/test_persistence_migration_gate.py")
    bundle = _text("tools/operational_release_bundle.py")
    assert 'expected_head() == "20260826_0042"' in migration_test
    assert "len(migrations) != EXPECTED_MIGRATION_COUNT" in bundle
    assert "len(entry_points) != EXPECTED_ENTRY_POINT_COUNT" in bundle
    assert "len(operators) != EXPECTED_OPERATOR_FILE_COUNT" in bundle


def test_historical_blocker_audit_is_superseded_by_explicit_later_closure():
    roadmap = _text("docs/technical-status-and-roadmap.md")
    blocked = roadmap.index("- LQ-277 release-publication operational readiness audit:")
    closed = roadmap.index("- LQ-285 release-publication end-to-end readiness")
    environment = roadmap.index("- LQ-287 evidence-based offline provider readiness")
    assert blocked < closed < environment
    lq285 = _text(
        "docs/lq-285-release-publication-end-to-end-readiness-and-runbook-handoff.md"
    )
    assert "interne Release-Publication-Prozesskette ist operativ geschlossen" in lq285
    assert "keine Freigabe eines konkreten externen Paketproviders" in lq285


def test_compose_status_names_the_real_remaining_non_release_worker_gap():
    readme = _text("operations/compose/README.md")
    compose = _text("operations/compose/compose.yaml")
    project = _text("pyproject.toml")
    assert "now supplies the `liquent-research-worker` command" in readme
    assert "liquent-research-worker" in compose
    assert "liquent-research-worker =" in project
    assert "LQ-058 must supply" not in readme
    assert "LQ-058 supplies" not in compose
    assert "offline Publication operator" in readme
