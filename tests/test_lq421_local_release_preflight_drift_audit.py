from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import signal
from unittest.mock import patch

from tools.controlled_release_preflight import PHASES, ControlledReleasePreflight
from tools.local_release_preflight_gates import local_gate_adapters, LocalGateContext, CommandResult
from tools.operational_release_bundle import (
    EXPECTED_ENTRY_POINT_COUNT,
    EXPECTED_MIGRATION_COUNT,
    EXPECTED_OPERATOR_FILE_COUNT,
)


ROOT = Path(__file__).parents[1]
COMMIT = "a" * 40


class Gate:
    def __init__(self, phase: str) -> None:
        self.phase = phase

    def execute(self, workspace: Path) -> bytes:
        created = {
            "distributions": "artifacts",
            "entrypoints": "installed-wheel",
            "sdist": "sdist-wheel-roundtrip",
            "bundle": "bundle",
        }.get(self.phase)
        if created is not None:
            (workspace / created).mkdir(mode=0o700)
        facts = hashlib.sha256(self.phase.encode()).hexdigest()
        return (
            json.dumps(
                {
                    "facts_sha256": facts,
                    "phase": self.phase,
                    "schema_version": 1,
                    "source_commit": COMMIT,
                    "status": "passed",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("ascii")


def test_signal_at_atomic_replace_cannot_turn_visible_success_into_rejection(
    tmp_path: Path,
) -> None:
    original = os.rename

    def replace_then_signal(source: str, target: str, **kwargs) -> None:
        original(source, target, **kwargs)
        os.kill(os.getpid(), signal.SIGTERM)

    gates = {phase: Gate(phase) for phase in PHASES}
    output = tmp_path / "result"
    with patch("tools.controlled_release_preflight.os.rename", replace_then_signal):
        evidence = ControlledReleasePreflight(gates).run(output)

    assert evidence.is_file()
    assert json.loads(evidence.read_text(encoding="ascii"))["outcome"] == "passed"


def test_code_phase_and_adapter_inventory_are_exact() -> None:
    assert PHASES == (
        "runtime",
        "source",
        "normal_tests",
        "postgres_tests",
        "distributions",
        "wheel",
        "entrypoints",
        "sdist",
        "final_diff",
        "bundle",
    )
    context = LocalGateContext(
        ROOT, environment={}, command_runner=lambda *_: CommandResult(b"", b"")
    )
    assert tuple(local_gate_adapters(context)) == PHASES


def test_package_inventory_claims_still_match_repository() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    scripts = re.findall(r"^liquent-[a-z0-9-]+\s*=", project, re.MULTILINE)
    operators = list((ROOT / "src/liquent_platform/operators").glob("*.py"))
    migrations = list(
        (ROOT / "src/liquent_platform/persistence/alembic/versions").glob("*.py")
    )
    assert len(scripts) == EXPECTED_ENTRY_POINT_COUNT == 71
    assert len(operators) == EXPECTED_OPERATOR_FILE_COUNT == 71
    assert len(migrations) == EXPECTED_MIGRATION_COUNT == 42


def test_docs_tests_and_roadmap_cover_every_preflight_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(
        encoding="utf-8"
    )
    positions: list[int] = []
    for number in range(414, 422):
        documents = list((ROOT / "docs").glob(f"lq-{number}-*.md"))
        tests = list((ROOT / "tests").glob(f"test_lq{number}_*.py"))
        assert len(documents) == 1
        assert len(tests) == 1
        assert f"`docs/{documents[0].name}`" in roadmap
        positions.append(roadmap.index(f"- LQ-{number} "))
    assert positions == sorted(positions)


def test_local_command_remains_uninstalled_and_non_authorizing() -> None:
    joined = "\n".join(
        (
            (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
            (ROOT / ".github/workflows/quality.yml").read_text(encoding="utf-8"),
            (ROOT / "operations/compose/compose.yaml").read_text(encoding="utf-8"),
        )
    )
    assert "controlled-release-preflight" not in joined
    cli = (ROOT / "tools/run_controlled_release_preflight.py").read_text(
        encoding="utf-8"
    )
    assert '"publishing_authorized": False' in cli
    assert '"deployment_authorized": False' in cli
