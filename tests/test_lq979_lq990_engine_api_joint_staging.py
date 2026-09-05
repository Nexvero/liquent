from pathlib import Path
import subprocess
import pytest
import tools.engine_api_joint_compose_render_preflight as preflight
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable

ROOT = Path(__file__).parents[1]

def test_render_preflight_invokes_only_quiet_config(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: calls.append((command, kwargs)) or subprocess.CompletedProcess(command, 0))
    preflight.verify(Path("/base.yaml"), Path("/overlay.yaml"), Path("/env"))
    command, kwargs = calls[0]
    assert command[:2] == ("docker", "compose")
    assert command[-2:] == ("config", "--quiet")
    assert not set(command) & {"up", "create", "start", "run", "exec"}
    assert kwargs["shell"] is False and kwargs["timeout"] == 30
    assert kwargs["stdout"] is subprocess.DEVNULL and kwargs["stderr"] is subprocess.DEVNULL

@pytest.mark.parametrize("outcome", (1, 2, 125))
def test_render_failure_is_detail_free(monkeypatch, outcome):
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, outcome, stderr=b"secret"))
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        preflight.verify(Path("/base"), Path("/overlay"), Path("/env"))
    assert "secret" not in str(caught.value)

def test_render_timeout_or_missing_binary_is_detail_free(monkeypatch):
    for error in (subprocess.TimeoutExpired("docker", 30), FileNotFoundError("docker")):
        monkeypatch.setattr(subprocess, "run", lambda *args, value=error, **kwargs: (_ for _ in ()).throw(value))
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            preflight.verify(Path("/base"), Path("/overlay"), Path("/env"))

def test_runbook_contains_all_staging_gates():
    text = (ROOT / "docs/lq-984-joint-engine-api-staging-runbook.md").read_text()
    for fact in ("0600", "Docker socket", "config --quiet", "/live", "/ready", "SIGTERM", "forced Health failure", "forced proxy failure", "Production readiness remains false"):
        assert fact in text
    assert "12. Stagingservice" in text

def test_overlay_remains_separate_from_standard_stack():
    base = (ROOT / "operations/compose/compose.yaml").read_text()
    overlay = ROOT / "operations/compose/compose.supervisor-engine-api.yaml"
    assert overlay.is_file() and "supervisor-engine-api" not in base and "docker.sock" not in base
