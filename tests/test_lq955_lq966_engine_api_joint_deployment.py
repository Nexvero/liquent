from pathlib import Path
import re
import pytest
import tools.engine_api_joint_deployment_preflight as preflight
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable

ROOT = Path(__file__).parents[1]

def test_packaging_inventory_remains_intentionally_unchanged():
    project = (ROOT / "pyproject.toml").read_text()
    assert len(re.findall(r"^liquent-[a-z0-9-]+\s*=", project, re.MULTILINE)) == 71
    assert "liquent-supervisor-engine-api-joint" not in project
    module = (ROOT / "src/liquent_platform/transport/manifest_handoff_supervisor_engine_api_joint_entrypoint.py").read_text()
    assert 'if __name__ == "__main__"' in module

def test_new_deployment_examples_are_exact_and_nonsecret():
    joint = (ROOT / "operations/compose/engine-api-joint.env.example").read_text()
    run = (ROOT / "operations/compose/engine-api-health-run.env.example").read_text()
    assert len(joint.splitlines()) == 5 and len(run.splitlines()) == 1
    assert "PASSWORD" not in joint + run and "SECRET" not in joint + run
    assert "/run/liquent/config/engine-api-proxy.env" in joint
    proxy = (ROOT / "operations/compose/engine-api-proxy.env.example").read_text()
    health = (ROOT / "operations/compose/engine-api-health.env.example").read_text()
    assert len(proxy.splitlines()) == 21 and len(health.splitlines()) == 9
    assert "PASSWORD" not in proxy + health and "SECRET" not in proxy + health

def test_preflight_loads_all_four_sources_in_order(monkeypatch):
    events = []
    joint = type("Joint", (), {"proxy_settings_file":Path("/run/liquent/config/engine-api-proxy.env"),"health_authority_file":Path("/run/liquent/config/engine-api-health.env"),"health_run_settings_file":Path("/run/liquent/config/engine-api-health-run.env")})()
    proxy = type("Proxy", (), {"proxy_socket":Path("/run/liquent/engine.sock"),"maximum_exchanges":1})()
    health = type("Health", (), {"socket_path":Path("/run/liquent/health.sock")})()
    run = type("Run", (), {"maximum_exchanges":1})()
    monkeypatch.setattr(preflight, "load_manifest_handoff_supervisor_engine_api_joint_settings", lambda path: events.append("joint") or joint)
    monkeypatch.setattr(preflight, "load_manifest_handoff_supervisor_engine_api_proxy_settings", lambda path: events.append("proxy") or proxy)
    monkeypatch.setattr(preflight, "load_manifest_handoff_supervisor_engine_api_health_authority", lambda path: events.append("health") or health)
    monkeypatch.setattr(preflight, "load_manifest_handoff_supervisor_engine_api_health_run_settings", lambda path: events.append("run") or run)
    preflight.verify(*(Path(f"/{name}") for name in ("joint","proxy","health","run")))
    assert events == ["joint", "proxy", "health", "run"]

def test_preflight_rejects_same_socket_or_wrong_container_bindings(monkeypatch):
    joint = type("Joint", (), {"proxy_settings_file":Path("/wrong"),"health_authority_file":Path("/wrong2"),"health_run_settings_file":Path("/wrong3")})()
    monkeypatch.setattr(preflight, "load_manifest_handoff_supervisor_engine_api_joint_settings", lambda path: joint)
    monkeypatch.setattr(preflight, "load_manifest_handoff_supervisor_engine_api_proxy_settings", lambda path: type("P", (), {"proxy_socket":Path("/same"),"maximum_exchanges":1})())
    monkeypatch.setattr(preflight, "load_manifest_handoff_supervisor_engine_api_health_authority", lambda path: type("H", (), {"socket_path":Path("/same")})())
    monkeypatch.setattr(preflight, "load_manifest_handoff_supervisor_engine_api_health_run_settings", lambda path: type("R", (), {"maximum_exchanges":1})())
    with pytest.raises(ManifestHandoffRegistryUnavailable): preflight.verify(*(Path(f"/{n}") for n in "abcd"))

def test_preflight_cli_is_detail_free(monkeypatch):
    monkeypatch.setattr(preflight, "verify", lambda *args: None)
    args = ["--joint-file","/j","--proxy-file","/p","--health-file","/h","--health-run-file","/r"]
    assert preflight.main(args) == 0
    monkeypatch.setattr(preflight, "verify", lambda *args: (_ for _ in ()).throw(RuntimeError("secret")))
    assert preflight.main(args) == 2
