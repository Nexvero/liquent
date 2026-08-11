from dataclasses import FrozenInstanceError, fields

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority import (
    InternalUserRecord,
    InternalUserStatus,
    WorkspaceOnboardingAuthorityRecord,
    WorkspaceOnboardingAuthorityStatus,
    WorkspaceRecord,
    WorkspaceStatus,
)
from liquent_platform.identity.research import WorkspaceId


USER = UserId("user-1")
WORKSPACE = WorkspaceId("workspace-1")


def test_the_three_status_types_are_separate_closed_vocabularies() -> None:
    assert [(item.name, item.value) for item in InternalUserStatus] == [
        ("ACTIVE", "active"),
        ("INACTIVE", "inactive"),
    ]
    assert [(item.name, item.value) for item in WorkspaceStatus] == [
        ("ACTIVE", "active"),
        ("INACTIVE", "inactive"),
    ]
    assert [(item.name, item.value) for item in WorkspaceOnboardingAuthorityStatus] == [
        ("ACTIVE", "active"),
        ("REVOKED", "revoked"),
    ]
    assert type(InternalUserStatus.ACTIVE) is not type(WorkspaceStatus.ACTIVE)


def test_records_are_frozen_slotted_hashable_and_repr_free_for_identifiers() -> None:
    records = [
        InternalUserRecord(USER, InternalUserStatus.ACTIVE),
        WorkspaceRecord(WORKSPACE, WorkspaceStatus.ACTIVE),
        WorkspaceOnboardingAuthorityRecord(
            USER, WORKSPACE, WorkspaceOnboardingAuthorityStatus.ACTIVE
        ),
    ]

    assert [tuple(field.name for field in fields(record)) for record in records] == [
        ("user_id", "status"),
        ("workspace_id", "status"),
        ("user_id", "workspace_id", "status"),
    ]
    assert all(hash(record) for record in records)
    assert all(not hasattr(record, "__dict__") for record in records)
    assert all("user-1" not in repr(record) for record in records)
    assert all("workspace-1" not in repr(record) for record in records)
    with pytest.raises(FrozenInstanceError):
        records[0].status = InternalUserStatus.INACTIVE  # type: ignore[misc]


@pytest.mark.parametrize(
    "record",
    [
        lambda value: InternalUserRecord(value, InternalUserStatus.ACTIVE),
        lambda value: WorkspaceRecord(value, WorkspaceStatus.ACTIVE),
        lambda value: WorkspaceOnboardingAuthorityRecord(
            value, WORKSPACE, WorkspaceOnboardingAuthorityStatus.ACTIVE
        ),
        lambda value: WorkspaceOnboardingAuthorityRecord(
            USER, value, WorkspaceOnboardingAuthorityStatus.ACTIVE
        ),
    ],
    ids=["user", "workspace", "authority-user", "authority-workspace"],
)
@pytest.mark.parametrize("value", ["", 1, True, b"x"], ids=["empty", "int", "bool", "bytes"])
def test_identifiers_must_be_nonempty_exact_strings(record: object, value: object) -> None:
    with pytest.raises(ValueError) as raised:
        record(value)  # type: ignore[operator]
    if value != "":
        assert str(value) not in str(raised.value)


@pytest.mark.parametrize(
    "record",
    [
        lambda: InternalUserRecord(USER, WorkspaceStatus.ACTIVE),
        lambda: WorkspaceRecord(WORKSPACE, InternalUserStatus.ACTIVE),
        lambda: WorkspaceOnboardingAuthorityRecord(
            USER, WORKSPACE, "active"  # type: ignore[arg-type]
        ),
    ],
    ids=["user", "workspace", "authority"],
)
def test_each_record_requires_its_exact_status_type(record: object) -> None:
    with pytest.raises(ValueError) as raised:
        record()  # type: ignore[operator]
    assert "active" not in str(raised.value)
