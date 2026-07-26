import pytest

from liquent_platform.identity.access import MembershipStatus, Permission
from liquent_platform.identity.authorization import permits_research


@pytest.mark.parametrize(
    ("granted", "required"),
    [
        ({Permission.RESEARCH_READ}, Permission.RESEARCH_READ),
        ({Permission.RESEARCH_WRITE}, Permission.RESEARCH_READ),
        ({Permission.RESEARCH_WRITE}, Permission.RESEARCH_WRITE),
    ],
)
def test_active_member_receives_only_granted_research_access(
    granted: set[Permission], required: Permission
) -> None:
    assert permits_research(MembershipStatus.ACTIVE, granted, required)


def test_read_permission_does_not_grant_write_access() -> None:
    assert not permits_research(
        MembershipStatus.ACTIVE,
        {Permission.RESEARCH_READ},
        Permission.RESEARCH_WRITE,
    )


@pytest.mark.parametrize("required", list(Permission))
def test_inactive_member_is_denied_even_when_permission_is_present(
    required: Permission,
) -> None:
    assert not permits_research(
        MembershipStatus.INACTIVE,
        set(Permission),
        required,
    )


@pytest.mark.parametrize("required", list(Permission))
def test_missing_permission_is_denied(required: Permission) -> None:
    assert not permits_research(MembershipStatus.ACTIVE, set(), required)
