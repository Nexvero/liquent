from pathlib import Path

ROOT = Path(__file__).parents[1]

def service():
    text = (ROOT / "operations/compose/compose.supervisor-engine-api.yaml").read_text()
    return text.split("  supervisor-engine-api:\n", 1)[1]

def test_service_is_explicit_profile_and_module_entrypoint():
    value = service()
    assert 'profiles: ["supervisor-engine-api"]' in value
    for part in ('command: ["python", "-m"', "manifest_handoff_supervisor_engine_api_joint_entrypoint", '"--settings-file"', '"/run/liquent/config/engine-api-joint.env"]'):
        assert part in value
    assert "ports:" not in value and "expose:" not in value

def test_service_identity_and_capabilities_are_minimal():
    value = service()
    assert 'user: "10001:10002"' in value and 'group_add: ["998"]' in value
    assert 'cap_drop: ["ALL"]' in value and "cap_add:" not in value
    assert 'security_opt: ["no-new-privileges:true"]' in value

def test_mount_inventory_is_exact_and_source_is_read_only():
    value = service()
    assert value.count("${LIQUENT_ENGINE_API_") == 8
    assert value.count(":/run/liquent/config/") == 4
    assert ":/srv/liquent/source:ro" in value
    assert ":/var/run/docker.sock" in value
    assert ":/srv/liquent/control:ro" not in value

def test_private_runtime_directory_and_shutdown_are_bounded():
    value = service()
    assert "/run/liquent:size=4m,mode=0700,uid=10001,gid=10002" in value
    assert "stop_grace_period: 15s" in value
    assert "init: true" in value and "read_only: true" in value

def test_healthcheck_is_private_unix_ready_probe():
    value = service()
    assert "AF_UNIX" in value and "/run/liquent/health.sock" in value
    assert "GET /ready" in value and " 200 " in value
    assert "timeout: 3s" in value and "retries: 6" in value

def test_runtime_environment_declares_all_eight_host_bindings():
    text = (ROOT / "operations/compose/supervisor-engine-api.env.example").read_text()
    assert text.count("LIQUENT_ENGINE_API_") == 8

def test_standard_compose_remains_closed():
    text = (ROOT / "operations/compose/compose.yaml").read_text()
    assert "supervisor-engine-api" not in text and "docker.sock" not in text
