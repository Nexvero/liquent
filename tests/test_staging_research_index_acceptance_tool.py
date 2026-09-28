import json

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexCheck,
)
from tools.staging_research_index_acceptance import main


def _input(tmp_path, outcome="passed"):
    path = tmp_path / "acceptance.json"
    path.write_text(json.dumps({
        "candidate_digest": "sha256:" + "b" * 64,
        "staging_origin": "https://staging.liquent.ai",
        "observed_at": "2026-09-15T12:00:00+00:00",
        "observations": [
            {"check": check.value, "outcome": outcome}
            for check in StagingResearchIndexCheck
        ],
    }))
    path.chmod(0o600)
    return path


def test_tool_emits_only_bound_accepted_result(tmp_path, capsys) -> None:
    assert main(["--input", str(_input(tmp_path))]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["outcome"] == "accepted"
    assert set(output) == {
        "candidate_digest", "staging_origin", "observed_at", "outcome"
    }


def test_tool_separates_rejected_and_unavailable(tmp_path, capsys) -> None:
    assert main(["--input", str(_input(tmp_path, "failed"))]) == 3
    assert json.loads(capsys.readouterr().out)["outcome"] == "rejected"
    assert main(["--input", str(_input(tmp_path, "unavailable"))]) == 4
    assert json.loads(capsys.readouterr().out)["outcome"] == "unavailable"


def test_tool_rejects_public_or_symbolic_input_without_output(
    tmp_path, capsys
) -> None:
    path = _input(tmp_path)
    path.chmod(0o644)
    assert main(["--input", str(path)]) == 2
    assert capsys.readouterr().out == ""
    path.chmod(0o600)
    link = tmp_path / "link.json"
    link.symlink_to(path)
    assert main(["--input", str(link)]) == 2
    assert capsys.readouterr().out == ""


def test_tool_rejects_extra_secret_field_without_output(tmp_path, capsys) -> None:
    path = _input(tmp_path)
    value = json.loads(path.read_text())
    value["cookie"] = "private"
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    assert main(["--input", str(path)]) == 2
    assert capsys.readouterr().out == ""
