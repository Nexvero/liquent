from pathlib import Path
import os
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "operations" / "research" / "staging-proof.sh"
EXAMPLE = ROOT / "operations" / "research" / "staging-proof.env.example"
RUNBOOK = ROOT / "operations" / "runbooks" / "staging-research-proof.md"


def test_script_has_valid_bash_syntax() -> None:
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


def test_check_mode_validates_without_runtime_mutation(tmp_path: Path) -> None:
    request = tmp_path / "request.json"
    request.write_text("{}", encoding="utf-8")
    config = tmp_path / "proof.env"
    config.write_text(EXAMPLE.read_text().replace(
        "/opt/liquent/evidence/identity-bootstrap/research-read-initial/membership-request.json",
        str(request),
    ), encoding="utf-8")
    config.chmod(0o600)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--check"], check=True, capture_output=True, text=True,
        env={**os.environ, "LIQUENT_RESEARCH_PROOF_CONFIG": str(config)},
    )
    assert result.stdout == "configuration valid; no mutation performed\n"


def test_revocation_denial_uses_defined_request_job_id() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert '${request_job_id}-denied' in script
    assert '${job_id}-denied' not in script
    assert "trap 'cleanup $?' EXIT" in script
    assert script.index("revoke_write\n") < script.index("denied_status=")
    assert "claim_count\"]!=1" in script
    assert "outcome_count\"]!=1" in script


def test_runbook_requires_revocation_and_post_revocation_denial() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "always attempts" in text
    assert "HTTP 403" in text
    assert "write_permission_revocation=failed" in text


def shell_function(name: str) -> str:
    script = SCRIPT.read_text(encoding="utf-8")
    body = script.split(f"{name}() {{", 1)[1].split("\n}\n", 1)[0]
    return f"{name}() {{{body}\n}}\n"


def test_revocation_failure_is_not_marked_successful() -> None:
    result = subprocess.run(["bash", "-c", shell_function("revoke_write") + """
docker() { return 17; }
CONTROL_PLANE_CONTAINER=test
revoke_done=0
if revoke_write; then exit 90; fi
[[ "$revoke_done" == 0 ]]
"""], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_membership_failure_stops_even_in_conditional_context() -> None:
    result = subprocess.run(["bash", "-c", shell_function("apply_membership") + """
docker() { return 17; }
put_in_container() { exit 90; }
CONTROL_PLANE_CONTAINER=test
container_dir=/tmp/test-proof
if apply_membership request revoke; then exit 91; fi
"""], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_cleanup_removes_session_secrets_and_reports_revocation_failure(tmp_path: Path) -> None:
    for name in ("session.json", "cookies.txt", "headers.txt"):
        (tmp_path / name).write_text("secret", encoding="utf-8")
    result = subprocess.run(["bash", "-c", shell_function("cleanup") + """
docker() { return 0; }
revoke_write() { return 1; }
grant_applied=1
revoke_done=0
CONTROL_PLANE_CONTAINER=test
container_dir=/tmp/test-proof
run_dir="$1"
cleanup 0
""", "test", str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "write_permission_revocation=failed" in result.stderr
    assert not list(tmp_path.iterdir())


def test_grant_is_guarded_before_application() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert 'grant_applied=1\n  apply_membership "$run_dir/grant-request.json" grant' in script
