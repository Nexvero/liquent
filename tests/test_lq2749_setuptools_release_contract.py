from pathlib import Path
import tomllib

from tools.local_release_preflight_gates import EXPECTED_SDIST_REQUIRES
from tools.verify_release_wheel import EXPECTED_REQUIRES_DIST


ROOT = Path(__file__).parents[1]


def _setuptools_specifiers(requirement: str) -> frozenset[str]:
    requirement = requirement.split(";", 1)[0].strip()
    assert requirement.startswith("setuptools")
    return frozenset(requirement.removeprefix("setuptools").split(","))


def test_setuptools_release_metadata_matches_project_dependency() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project_requirement = next(
        requirement
        for requirement in project["project"]["optional-dependencies"]["dev"]
        if requirement.startswith("setuptools")
    )
    wheel_requirement = next(
        requirement
        for requirement in EXPECTED_REQUIRES_DIST
        if requirement.startswith("setuptools")
    )
    sdist_requirement = next(
        requirement
        for requirement in EXPECTED_SDIST_REQUIRES.decode().splitlines()
        if requirement.startswith("setuptools")
    )

    expected = _setuptools_specifiers(project_requirement)
    assert expected == frozenset({">=80", "<85"})
    assert _setuptools_specifiers(wheel_requirement) == expected
    assert _setuptools_specifiers(sdist_requirement) == expected
