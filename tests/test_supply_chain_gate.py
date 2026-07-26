from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from tools.verify_image_sbom import verify


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "quality.yml"


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
        "only-fixed: false",
        "verify_image_sbom.py",
    ):
        assert term in workflow


def test_provenance_is_push_only_and_minimally_permissioned() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    block = workflow.split("  provenance:\n", 1)[1]
    assert "if: github.event_name == 'push'" in block
    assert "needs: container" in block
    assert "id-token: write" in block
    assert "attestations: write" in block
    assert "packages: write" not in workflow
    assert "docker push" not in workflow
