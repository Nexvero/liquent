from pathlib import Path
import pytest
import liquent_platform.transport.manifest_handoff_supervisor_engine_api_joint_entrypoint as entrypoint
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_joint_settings import ManifestHandoffSupervisorEngineApiJointSettings, load_manifest_handoff_supervisor_engine_api_joint_settings

VALUES = {"proxy_settings_file":"/private/proxy.env","health_authority_file":"/private/health.env","health_run_settings_file":"/private/run.env","poll_timeout_milliseconds":"250","join_timeout_milliseconds":"2000"}

def test_joint_settings_are_exact_and_bounded():
    value = ManifestHandoffSupervisorEngineApiJointSettings.from_mapping(VALUES)
    assert value.poll_timeout_seconds == .25 and value.join_timeout_seconds == 2.0
    assert repr(value) == "ManifestHandoffSupervisorEngineApiJointSettings()"

@pytest.mark.parametrize("change", ({"poll_timeout_milliseconds":"0"},{"join_timeout_milliseconds":"100"},{"poll_timeout_milliseconds":"0250"},{"extra":"x"}))
def test_joint_settings_reject_nonexact_values(change):
    values = dict(VALUES); values.update(change)
    with pytest.raises(ManifestHandoffRegistryUnavailable): ManifestHandoffSupervisorEngineApiJointSettings.from_mapping(values)

def test_owner_private_joint_source(tmp_path):
    path = tmp_path / "joint.env"
    path.write_text("".join(f"LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_ENGINE_API_JOINT_{key.upper()}={value}\n" for key, value in VALUES.items()))
    path.chmod(0o600)
    assert load_manifest_handoff_supervisor_engine_api_joint_settings(path).join_timeout_seconds == 2.0
    path.chmod(0o640)
    with pytest.raises(ManifestHandoffRegistryUnavailable): load_manifest_handoff_supervisor_engine_api_joint_settings(path)

def test_entrypoint_loads_composes_and_runs_exact_order(monkeypatch):
    settings = ManifestHandoffSupervisorEngineApiJointSettings.from_mapping(VALUES)
    proxy_settings, authority, run_settings = object(), object(), object()
    proxy = type("Proxy", (), {"observed_bundle": object()})()
    health, expected = object(), (object(), object())
    events = []
    monkeypatch.setattr(entrypoint, "load_manifest_handoff_supervisor_engine_api_joint_settings", lambda path: events.append(("joint", path)) or settings)
    monkeypatch.setattr(entrypoint, "load_manifest_handoff_supervisor_engine_api_proxy_settings", lambda path: events.append(("proxy-settings", path)) or proxy_settings)
    monkeypatch.setattr(entrypoint, "load_manifest_handoff_supervisor_engine_api_health_authority", lambda path: events.append(("authority", path)) or authority)
    monkeypatch.setattr(entrypoint, "load_manifest_handoff_supervisor_engine_api_health_run_settings", lambda path: events.append(("run-settings", path)) or run_settings)
    monkeypatch.setattr(entrypoint, "compose_manifest_handoff_supervisor_engine_api_poll_runtime", lambda value, **kw: events.append(("proxy", value, kw)) or proxy)
    monkeypatch.setattr(entrypoint, "compose_manifest_handoff_supervisor_engine_api_health_poll_runtime", lambda *args, **kw: events.append(("health", args, kw)) or health)
    class Owner:
        def __init__(self, *args, **kw): events.append(("owner", args, kw))
        def run(self): events.append("run"); return expected
    monkeypatch.setattr(entrypoint, "JointManifestHandoffSupervisorEngineApiProcessOwner", Owner)
    assert entrypoint.run_manifest_handoff_supervisor_engine_api_joint(Path("/private/joint.env")) is expected
    assert [item if item == "run" else item[0] for item in events] == ["joint","proxy-settings","authority","run-settings","proxy","health","owner","run"]

def test_cli_is_explicit_and_detail_free(monkeypatch):
    monkeypatch.setattr(entrypoint, "run_manifest_handoff_supervisor_engine_api_joint", lambda path: (object(), object()))
    assert entrypoint.main(["--settings-file", "/private/joint.env"]) == 0
    assert entrypoint.main([]) == 2
    monkeypatch.setattr(entrypoint, "run_manifest_handoff_supervisor_engine_api_joint", lambda path: (_ for _ in ()).throw(RuntimeError("secret")))
    assert entrypoint.main(["--settings-file", "/private/joint.env"]) == 2
