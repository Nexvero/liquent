from pathlib import Path

import pytest
from pydantic import ValidationError

from liquent_platform.configuration import PlatformSettings


def _settings(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "database_url": "sqlite://",
        "manifest_handoff_supervisor_mode": "candidate",
        "manifest_handoff_supervisor_backend_instance_id": "control-plane-a",
        "manifest_handoff_supervisor_docker_socket": Path("/run/docker.sock"),
        "manifest_handoff_supervisor_control_root": Path(
            "/run/liquent/supervisor-control"
        ),
        "manifest_handoff_supervisor_host_owner_uid": 10001,
        "manifest_handoff_supervisor_reader_gid": 10002,
        "manifest_handoff_supervisor_wrapper_uid": 10002,
        "manifest_handoff_supervisor_wrapper_gid": 10002,
    }
    values.update(changes)
    return values


def test_supervisor_settings_are_closed_by_default_and_value_free() -> None:
    settings = PlatformSettings(_secrets_dir=None)

    assert settings.manifest_handoff_supervisor_enabled is False
    assert settings.public_summary()["manifest_handoff_supervisor_enabled"] == "false"


def test_complete_candidate_settings_enable_only_the_settings_contract() -> None:
    settings = PlatformSettings(_secrets_dir=None, **_settings())

    assert settings.manifest_handoff_supervisor_enabled is True
    summary = settings.public_summary()
    assert summary["manifest_handoff_supervisor_enabled"] == "true"
    for private in ("docker.sock", "supervisor-control", "10001", "10002"):
        assert private not in str(summary)


@pytest.mark.parametrize(
    "field",
    (
        "manifest_handoff_supervisor_mode",
        "manifest_handoff_supervisor_backend_instance_id",
        "manifest_handoff_supervisor_docker_socket",
        "manifest_handoff_supervisor_control_root",
        "manifest_handoff_supervisor_host_owner_uid",
        "manifest_handoff_supervisor_reader_gid",
        "manifest_handoff_supervisor_wrapper_uid",
        "manifest_handoff_supervisor_wrapper_gid",
    ),
)
def test_partial_supervisor_settings_fail_before_process_composition(field: str) -> None:
    values = _settings()
    values.pop(field)
    with pytest.raises(ValidationError, match="must be provided together"):
        PlatformSettings(_secrets_dir=None, **values)


@pytest.mark.parametrize(
    "changes",
    (
        {"manifest_handoff_supervisor_mode": "legacy"},
        {"manifest_handoff_supervisor_backend_instance_id": "INVALID ID"},
        {"manifest_handoff_supervisor_docker_socket": Path("docker.sock")},
        {"manifest_handoff_supervisor_docker_socket": Path("/")},
        {"manifest_handoff_supervisor_docker_socket": Path("/run/../docker.sock")},
        {"manifest_handoff_supervisor_control_root": Path("control")},
        {"manifest_handoff_supervisor_control_root": Path("/")},
        {
            "manifest_handoff_supervisor_control_root": Path("/run/docker.sock")
        },
        {"manifest_handoff_supervisor_host_owner_uid": 0},
        {"manifest_handoff_supervisor_wrapper_uid": 10001},
        {"manifest_handoff_supervisor_wrapper_gid": 10003},
    ),
)
def test_invalid_paths_mode_or_identity_fail_closed(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        PlatformSettings(_secrets_dir=None, **_settings(**changes))


def test_candidate_settings_require_the_shared_database_configuration() -> None:
    values = _settings()
    values.pop("database_url")
    with pytest.raises(ValidationError, match="requires the database_url"):
        PlatformSettings(_secrets_dir=None, **values)


def test_runtime_example_lists_the_atomic_group_without_activating_it() -> None:
    example = (
        Path(__file__).parents[1] / "operations/compose/runtime.env.example"
    ).read_text(encoding="utf-8")
    fields = (
        field for field in PlatformSettings.model_fields
        if field.startswith("manifest_handoff_supervisor_")
    )
    for field in fields:
        assert f"# LIQUENT_{field.upper()}=" in example
