import os
from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import ManifestHandoffSupervisorEngineApiProcessBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_authority import ManifestHandoffSupervisorEngineApiHealthSocketAuthority
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_run_settings import ManifestHandoffSupervisorEngineApiHealthRunSettings
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_run_settings_source import load_manifest_handoff_supervisor_engine_api_health_run_settings
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_runtime_composition import compose_manifest_handoff_supervisor_engine_api_health_runtime


def private_file(path, value="100"):
    path.write_text(f"LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_ENGINE_API_HEALTH_MAXIMUM_EXCHANGES={value}\n")
    path.chmod(0o600)
    return path


def test_exact_run_settings_are_closed_and_detail_free():
    value = ManifestHandoffSupervisorEngineApiHealthRunSettings.from_mapping(
        {"maximum_exchanges": "100"}
    )
    assert value.maximum_exchanges == 100
    assert repr(value) == "ManifestHandoffSupervisorEngineApiHealthRunSettings()"


@pytest.mark.parametrize("mapping", ({}, {"maximum_exchanges": "0"},
    {"maximum_exchanges": "01"}, {"maximum_exchanges": "1000001"},
    {"maximum_exchanges": "1", "extra": "2"}))
def test_nonexact_run_settings_fail_closed(mapping):
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        ManifestHandoffSupervisorEngineApiHealthRunSettings.from_mapping(mapping)


def test_private_source_loads_exact_settings(tmp_path):
    assert load_manifest_handoff_supervisor_engine_api_health_run_settings(
        private_file(tmp_path / "run.env")
    ).maximum_exchanges == 100


def test_source_rejects_mode_link_and_process_environment(tmp_path, monkeypatch):
    path = private_file(tmp_path / "run.env")
    path.chmod(0o640)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        load_manifest_handoff_supervisor_engine_api_health_run_settings(path)
    source = private_file(tmp_path / "source.env")
    link = tmp_path / "link.env"; os.link(source, link)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        load_manifest_handoff_supervisor_engine_api_health_run_settings(source)
    monkeypatch.setenv("LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_ENGINE_API_HEALTH_MAXIMUM_EXCHANGES", "999")
    link.unlink()
    assert load_manifest_handoff_supervisor_engine_api_health_run_settings(source).maximum_exchanges == 100


def test_runtime_composition_retains_observed_process_identity():
    process = object.__new__(ManifestHandoffSupervisorEngineApiProcessBundle)
    authority = ManifestHandoffSupervisorEngineApiHealthSocketAuthority(
        Path("/run/liquent/health.sock"), 100, 101, 100, 101, 102, 103, 5, 8
    )
    owner = compose_manifest_handoff_supervisor_engine_api_health_runtime(
        process, authority, ManifestHandoffSupervisorEngineApiHealthRunSettings(7)
    )
    transport = owner._bundle.transport
    assert transport.health.process_bundle is process
    assert transport.health.owner._bundle is process
    assert transport.serve_loop._maximum == 7


def test_runtime_composition_rejects_foreign_dependencies():
    authority = ManifestHandoffSupervisorEngineApiHealthSocketAuthority(
        Path("/run/liquent/health.sock"), 100, 101, 100, 101, 102, 103, 5, 8
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        compose_manifest_handoff_supervisor_engine_api_health_runtime(
            object(), authority, ManifestHandoffSupervisorEngineApiHealthRunSettings(1)
        )
