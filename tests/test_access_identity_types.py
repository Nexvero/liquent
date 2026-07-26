from liquent_platform.identity.access import MembershipStatus, Permission, UserId


def test_user_id_is_a_distinct_semantic_string_type() -> None:
    assert UserId("user-1") == "user-1"


def test_membership_status_has_only_the_required_states() -> None:
    assert {status.value for status in MembershipStatus} == {"active", "inactive"}


def test_permission_has_only_the_two_research_values() -> None:
    assert {permission.value for permission in Permission} == {
        "research:read",
        "research:write",
    }
