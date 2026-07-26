from __future__ import annotations

import json
from datetime import date
from pathlib import Path
import re

import pytest

from tools.verify_image_sbom import verify


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "quality.yml"
GRYPE_CONFIG = ROOT / ".grype.yaml"


def _sbom() -> dict[str, object]:
    return {
        "spdxVersion": "SPDX-2.3",
        "SPDXID": "SPDXRef-DOCUMENT",
        "documentNamespace": "https://liquent.ai/sbom/test",
        "packages": [{"name": "liquent", "versionInfo": "0.0.1"}],
    }


def test_valid_liquent_sbom_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "sbom.json"
    path.write_text(json.dumps(_sbom()), encoding="utf-8")
    assert re.fullmatch(r"[0-9a-f]{64}", verify(path))


@pytest.mark.parametrize("mutation", ["empty", "identity", "namespace", "secret"])
def test_incomplete_or_sensitive_sbom_is_rejected(tmp_path: Path, mutation: str) -> None:
    document = _sbom()
    if mutation == "empty":
        document["packages"] = []
    elif mutation == "identity":
        document["packages"] = [{"name": "something-else"}]
    elif mutation == "namespace":
        document["documentNamespace"] = ""
    else:
        document["files"] = [{"fileName": "/operations/secrets/token"}]
    path = tmp_path / "sbom.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(SystemExit, match="SBOM verification failed"):
        verify(path)


def test_supply_chain_tools_and_versions_are_explicit() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    for term in (
        "syft-version: v1.44.0",
        "grype-version: v0.112.0",
        "severity-cutoff: high",
        "only-fixed: true",
        "config: .grype.yaml",
        "verify_image_sbom.py",
    ):
        assert term in workflow


def test_grype_exception_is_narrow_owned_and_time_bounded() -> None:
    config = GRYPE_CONFIG.read_text(encoding="utf-8")
    assert "exception-owner: Liquent Platform Architecture" in config
    assert "vulnerability: CVE-2026-15308" in config
    assert "name: python" in config
    assert "version: 3.13.14" in config
    assert config.count("- vulnerability:") == 1
    expiry = date.fromisoformat(
        config.split("exception-expires: ", 1)[1].splitlines()[0]
    )
    assert date.today() <= expiry <= date(2026, 9, 30)


def test_provenance_is_push_only_and_minimally_permissioned() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    block = workflow.split("  provenance:\n", 1)[1]
    assert "if: github.event_name == 'push'" in block
    assert "needs: container" in block
    assert "id-token: write" in block
    assert "attestations: write" in block
    assert "packages: write" not in workflow
    assert "docker push" not in workflow
