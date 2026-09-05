from pathlib import Path

import pytest

import liquent_platform.transport.manifest_handoff_supervisor_engine_api_entrypoint as operator
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import (
    ManifestHandoffSupervisorEngineApiServeResult,
)


class Process:
    def __init__(self, result=None, failure=None) -> None:
        self.result = result or ManifestHandoffSupervisorEngineApiServeResult(3, "stopped")
        self.failure = failure
        self.runs = 0

    def run(self):
        self.runs += 1
        if self.failure is not None:
            raise self.failure
        return self.result


class Settings:
    maximum_exchanges = 10


class Bundle:
    def __init__(self, process) -> None:
        self.process_run = process


def test_run_loads_composes_and_runs_once_in_fixed_identity_order(monkeypatch) -> None:
    path = Path("/private/proxy.env")
    settings, process, calls = Settings(), Process(), []

    def load(current):
        calls.append(("load", current))
        return settings

    def compose(current):
        calls.append(("compose", current))
        return Bundle(process)

    monkeypatch.setattr(operator, "load_manifest_handoff_supervisor_engine_api_proxy_settings", load)
    monkeypatch.setattr(operator, "compose_manifest_handoff_supervisor_engine_api_proxy_bundle", compose)
    result = operator.run_manifest_handoff_supervisor_engine_api_proxy(path)
    assert result == ManifestHandoffSupervisorEngineApiServeResult(3, "stopped")
    assert calls == [("load", path), ("compose", settings)]
    assert process.runs == 1


@pytest.mark.parametrize("stage", ("load", "compose", "run"))
def test_each_failed_stage_stops_the_chain_and_is_detail_free(monkeypatch, stage) -> None:
    calls = []
    settings, process = Settings(), Process()

    def load(path):
        calls.append("load")
        if stage == "load":
            raise RuntimeError("private load detail")
        return settings

    def compose(value):
        calls.append("compose")
        if stage == "compose":
            raise RuntimeError("private composition detail")
        if stage == "run":
            process.failure = RuntimeError("private run detail")
        return Bundle(process)

    monkeypatch.setattr(operator, "load_manifest_handoff_supervisor_engine_api_proxy_settings", load)
    monkeypatch.setattr(operator, "compose_manifest_handoff_supervisor_engine_api_proxy_bundle", compose)
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operator.run_manifest_handoff_supervisor_engine_api_proxy(Path("/private/proxy.env"))
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert calls == (["load"] if stage == "load" else ["load", "compose"])


@pytest.mark.parametrize("result", (
    None,
    object(),
    ManifestHandoffSupervisorEngineApiServeResult(-1, "stopped"),
    ManifestHandoffSupervisorEngineApiServeResult(11, "stopped"),
    ManifestHandoffSupervisorEngineApiServeResult(9, "exchange_limit"),
    ManifestHandoffSupervisorEngineApiServeResult(3, "unknown"),
))
def test_noncontractual_run_result_fails_closed(monkeypatch, result) -> None:
    monkeypatch.setattr(
        operator, "load_manifest_handoff_supervisor_engine_api_proxy_settings",
        lambda path: Settings(),
    )
    process = Process()
    process.result = result
    monkeypatch.setattr(
        operator, "compose_manifest_handoff_supervisor_engine_api_proxy_bundle",
        lambda settings: Bundle(process),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        operator.run_manifest_handoff_supervisor_engine_api_proxy(
            Path("/private/proxy.env")
        )


def test_main_accepts_only_one_explicit_settings_file(monkeypatch) -> None:
    seen = []
    monkeypatch.setattr(
        operator, "run_manifest_handoff_supervisor_engine_api_proxy",
        lambda path: seen.append(path),
    )
    assert operator.main(["--settings-file", "/private/proxy.env"]) == 0
    assert seen == [Path("/private/proxy.env")]
    for arguments in ([], ["/private/proxy.env"], ["--settings-file", "a", "extra"]):
        assert operator.main(arguments) == 2
    assert seen == [Path("/private/proxy.env")]


def test_main_returns_only_detail_free_failure_code(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        operator, "run_manifest_handoff_supervisor_engine_api_proxy",
        lambda path: (_ for _ in ()).throw(RuntimeError("private detail")),
    )
    assert operator.main(["--settings-file", "/private/proxy.env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_source_has_no_environment_default_or_deployment_coupling() -> None:
    source = Path(operator.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "os.environ", "getenv(", "default=", "PlatformSettings", "compose.yaml",
        "create_app", "database", "production_ready",
    ):
        assert forbidden not in source
