from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from liquent_platform.application.internal_destination import (
    ValidatedInternalDestination,
    resolve_internal_destination,
)

VALID = ["/", "/workspaces/w-1/research", "/users/user_1", "/reports/v1.2", "/a/~draft"]


class LoudStr(str):
    """A str subclass, to pin the deliberate exact-type boundary."""


def test_a_missing_return_path_resolves_to_the_fixed_default() -> None:
    result = resolve_internal_destination(None)

    assert result is not None
    assert result.value == "/"


@pytest.mark.parametrize("path", VALID)
def test_valid_paths_pass_through_unchanged(path: str) -> None:
    result = resolve_internal_destination(path)

    assert result is not None
    # Identity, not equality: nothing is normalized, rewritten, or rebuilt.
    assert result.value is path


@pytest.mark.parametrize(
    "path",
    ["https://evil.test", "//evil.test", "///evil.test", "/\\evil.test",
     "\\evil.test", "relative"],
)
def test_cross_origin_and_relative_references_are_refused(path: str) -> None:
    assert resolve_internal_destination(path) is None


@pytest.mark.parametrize(
    "path",
    ["/a?next=//evil.test", "/a#fragment", "/%2f%2fevil.test", "/%5cevil.test",
     "/a b", "/a\tb", "/a\nb", "/tökén"],
)
def test_query_fragment_percent_whitespace_and_non_ascii_are_refused(
    path: str,
) -> None:
    assert resolve_internal_destination(path) is None


@pytest.mark.parametrize(
    "path", ["", "/a//b", "/a/", "/.", "/..", "/a/../b", "/a/./b"]
)
def test_empty_double_trailing_and_dot_segments_are_refused(path: str) -> None:
    assert resolve_internal_destination(path) is None


@pytest.mark.parametrize("length", [2048, 2049])
def test_the_length_limit_is_exact(length: int) -> None:
    path = "/" + "a" * (length - 1)
    assert len(path) == length

    result = resolve_internal_destination(path)

    assert (result.value if result else None) is (path if length == 2048 else None)


@pytest.mark.parametrize(
    "value", [b"/a", 1, ["/a"], LoudStr("/a")], ids=["bytes", "int", "list", "subclass"]
)
def test_non_strings_are_refused_neutrally(value: Any) -> None:
    assert resolve_internal_destination(value) is None


def test_the_value_object_is_frozen_slotted_hashable_and_refuses_invalid_values() -> None:
    destination = ValidatedInternalDestination("/a/b")

    with pytest.raises(FrozenInstanceError):
        destination.value = "/elsewhere"  # type: ignore[misc]
    assert ValidatedInternalDestination.__slots__ == ("value",)
    assert hash(destination) == hash(ValidatedInternalDestination("/a/b"))
    assert repr(destination) == "ValidatedInternalDestination()"

    for rejected in ("//evil.test", "/a/../b"):
        with pytest.raises(ValueError) as raised:
            ValidatedInternalDestination(rejected)
        assert str(raised.value) == "invalid internal destination"
        assert rejected not in str(raised.value)
        assert raised.value.__cause__ is None and raised.value.__context__ is None
