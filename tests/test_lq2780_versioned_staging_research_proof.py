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
