import ast
from pathlib import Path

import pytest

from liquent_platform.application.manifest_handoff_supervisor_candidate_composition import (
    CandidateManifestHandoffSupervisorGraph,
    compose_candidate_manifest_handoff_supervisor_graph,
)
from liquent_platform.application.manifest_handoff_supervisor_child_process import (
    OneShotManifestHandoffSupervisorChildProcess,
)
from liquent_platform.application.manifest_handoff_supervisor_execution_reconciliation import (
    ReadOnlyManifestHandoffSupervisorExecutionReconciler,
)
from liquent_platform.application.manifest_handoff_supervisor_observation_parent import (
    ObservationOnlyManifestHandoffSupervisorReleaseService,
)
from liquent_platform.application.manifest_handoff_supervisor_observation_terminal import (
    ObservationOnlyManifestHandoffSupervisorTerminalService,
)
from liquent_platform.application.manifest_handoff_supervisor_parent_launch import (
    CandidateObservationOnlyManifestHandoffSupervisorPrepareService,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_candidate_composition.py"


class Inert:
    def __getattr__(self, name):
        raise AssertionError(f"composition performed I/O through {name}")


def compose():
    dependency = Inert()
    return compose_candidate_manifest_handoff_supervisor_graph(
        journal=dependency, runtime_bindings=dependency,
        gate_bindings=dependency, supervisor_engine=dependency,
        control_artifacts=dependency, launch_documents=dependency,
        launch_loader=dependency,
        child_capability_executor=dependency,
        clock=lambda: None, monotonic=lambda: 0.0, sleep=lambda seconds: None,
        maximum_release_wait=10, poll_interval=1,
    )


def test_candidate_composition_is_inert_and_returns_closed_bundle():
    graph = compose()
    assert type(graph) is CandidateManifestHandoffSupervisorGraph
    assert type(graph.prepare) is CandidateObservationOnlyManifestHandoffSupervisorPrepareService
    assert type(graph.release) is ObservationOnlyManifestHandoffSupervisorReleaseService
    assert type(graph.child) is OneShotManifestHandoffSupervisorChildProcess
    assert type(graph.terminal) is ObservationOnlyManifestHandoffSupervisorTerminalService
    assert type(graph.reconciliation) is ReadOnlyManifestHandoffSupervisorExecutionReconciler
    assert graph.terminal_observation_complete is True
    assert graph.production_ready is False


def test_candidate_repr_discloses_no_dependencies():
    value = compose()
    representation = repr(value)
    assert "Inert" not in representation
    assert "executor" not in representation


def test_composition_imports_no_compatibility_prepare_release_or_service():
    text = SOURCE.read_text(encoding="utf-8")
    for forbidden in (
        "PersistentManifestHandoffSupervisorPrepareService",
        "PersistentManifestHandoffSupervisorReleaseService",
        "PersistentManifestHandoffSupervisorService",
        "compose_persistent_manifest_handoff_supervisor_service",
    ):
        assert forbidden not in text


def test_only_child_receives_capability_executor():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    executor_keywords = [keyword for call in calls for keyword in call.keywords
                         if keyword.arg == "executor"]
    assert len(executor_keywords) == 1
    assert ast.unparse(executor_keywords[0].value) == "child_capability_executor"
    text = SOURCE.read_text(encoding="utf-8")
    assert "capability_executor=" not in text


def test_parent_release_receives_publisher_but_no_child_executor():
    text = SOURCE.read_text(encoding="utf-8")
    start = text.index("release = ObservationOnlyManifestHandoffSupervisorReleaseService(")
    end = text.index("child = OneShotManifestHandoffSupervisorChildProcess(")
    release = text[start:end]
    assert "publisher=control_artifacts" in release
    assert "executor" not in release


def test_terminal_and_production_claims_cannot_be_overridden():
    graph = compose()
    with pytest.raises((TypeError, AttributeError)):
        graph.production_ready = True
    with pytest.raises(TypeError):
        CandidateManifestHandoffSupervisorGraph(
            graph.prepare, graph.release, graph.child, graph.terminal,
            graph.reconciliation, terminal_observation_complete=False,
        )


def test_incomplete_dependencies_fail_before_io_detail_free():
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        compose_candidate_manifest_handoff_supervisor_graph(
            journal=None, runtime_bindings=Inert(), gate_bindings=Inert(),
            supervisor_engine=Inert(), control_artifacts=Inert(),
            launch_documents=Inert(), launch_loader=Inert(),
            child_capability_executor=Inert(),
            clock=lambda: None, monotonic=lambda: 0.0, sleep=lambda seconds: None,
            maximum_release_wait=10, poll_interval=1,
        )
    assert str(caught.value) == "manifest_handoff_registry_unavailable"


def test_no_settings_appfactory_compose_cli_or_actor_authority():
    text = SOURCE.read_text(encoding="utf-8")
    for forbidden in ("SessionPrincipal", "Permission", "allow", "settings",
                      "create_app", "argparse", "docker", "sqlalchemy"):
        assert forbidden not in text
