from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from tools.controlled_release_preflight import (
    EVIDENCE_NAME,
    PHASES,
    ControlledPreflightRejected,
    ControlledReleasePreflight,
)
from tools.run_controlled_release_preflight import compose_local_preflight, main


ROOT = Path(__file__).parents[1]


def test_composition_binds_exact_local_gate_set_without_execution() -> None:
    preflight = compose_local_preflight(ROOT)
    assert isinstance(preflight, ControlledReleasePreflight)
    assert tuple(preflight._gates) == PHASES


def test_success_output_is_bounded_and_never_authorizes_external_actions(
    tmp_path: Path, capsys=None
) -> None:
    evidence = tmp_path / "private-result" / EVIDENCE_NAME
    with patch(
        "tools.run_controlled_release_preflight.run_local_preflight",
        return_value=evidence,
    ), patch("builtins.print") as printed:
        result = main(
            [
                "--source-root",
                str(ROOT),
                "--output-directory",
                str(tmp_path / "private-result"),
            ]
        )

    assert result == 0
    document = json.loads(printed.call_args.args[0])
    assert document == {
        "deployment_authorized": False,
        "evidence": EVIDENCE_NAME,
        "outcome": "passed",
        "publishing_authorized": False,
    }
    assert str(tmp_path) not in printed.call_args.args[0]


def test_rejection_is_constant_and_contains_no_source_or_output_path(tmp_path: Path) -> None:
    with patch(
        "tools.run_controlled_release_preflight.run_local_preflight",
        side_effect=ControlledPreflightRejected(
            f"secret failure at {tmp_path}"
        ),
    ), patch("builtins.print") as printed:
        result = main(
            [
                "--source-root",
                str(tmp_path / "source"),
                "--output-directory",
                str(tmp_path / "output"),
            ]
        )

    assert result == 2
    assert json.loads(printed.call_args.args[0]) == {
        "error": "controlled_release_preflight_rejected"
    }
    assert str(tmp_path) not in printed.call_args.args[0]


def test_cli_exposes_no_command_dependency_or_authority_overrides() -> None:
    source = (ROOT / "tools/run_controlled_release_preflight.py").read_text(
        encoding="utf-8"
    )
    assert "--source-root" in source
    assert "--output-directory" in source
    for forbidden in (
        "--command",
        "--python",
        "--dsn",
        "--install",
        "--skip",
        "--allow",
        "--publish",
        "--deploy",
    ):
        assert forbidden not in source


def test_command_is_not_installed_or_automatically_wired() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/quality.yml").read_text(encoding="utf-8")
    compose = (ROOT / "operations/compose/compose.yaml").read_text(encoding="utf-8")
    command = "controlled-release-preflight"
    assert command not in project
    assert command not in workflow
    assert command not in compose
