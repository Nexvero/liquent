from dataclasses import FrozenInstanceError, fields

import pytest

from liquent_platform.identity.admission import IdentityAdmissionId


def test_valid_admission_id_holds_exact_value() -> None:
    admission = IdentityAdmissionId("admission-abc-123")

    assert admission.value == "admission-abc-123"


def test_empty_admission_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="admission id must not be empty"):
        IdentityAdmissionId("")


def test_value_is_not_normalized() -> None:
    raw = "  Admission/ABC//Def  "
    admission = IdentityAdmissionId(raw)

    # No trimming, lowercasing, or slash normalization.
    assert admission.value == raw


def test_case_or_slash_difference_is_a_distinct_admission_id() -> None:
    base = IdentityAdmissionId("admission-1")

    assert base != IdentityAdmissionId("Admission-1")
    assert base != IdentityAdmissionId("admission-1/")


def test_admission_id_is_immutable() -> None:
    admission = IdentityAdmissionId("admission-1")

    with pytest.raises(FrozenInstanceError):
        admission.value = "other"  # type: ignore[misc]


def test_admission_id_is_hashable() -> None:
    admission = IdentityAdmissionId("admission-1")

    assert hash(admission) == hash(IdentityAdmissionId("admission-1"))
    assert {admission: 1}[IdentityAdmissionId("admission-1")] == 1


def test_model_holds_only_value() -> None:
    names = [field.name for field in fields(IdentityAdmissionId)]

    assert names == ["value"]


def test_value_is_absent_from_repr() -> None:
    # A sensitive capability handle must not reach logs or error diagnostics
    # through an object representation.
    text = repr(IdentityAdmissionId("secret-admission"))

    assert "secret-admission" not in text


def test_class_name_may_appear_in_repr() -> None:
    text = repr(IdentityAdmissionId("secret-admission"))

    assert "IdentityAdmissionId" in text


def test_value_stays_available_for_authorized_internal_processing() -> None:
    admission = IdentityAdmissionId("secret-admission")

    # Hidden from repr, but unchanged via the attribute.
    assert admission.value == "secret-admission"
