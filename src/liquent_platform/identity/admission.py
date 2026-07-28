"""The opaque reference to one internally issued identity admission."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IdentityAdmissionId:
    """An opaque handle to a previously issued internal admission.

    The value is stored verbatim: no trimming, lowercasing, or normalization.
    The object carries no admission state. Presenting this handle determines
    neither the target user nor any permission; target, validity, expiry, and
    consumption state are resolved exclusively from Liquent's internal state.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("admission id must not be empty")
