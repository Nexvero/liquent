"""The opaque reference to one internally issued identity admission."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IdentityAdmissionId:
    """An opaque handle to a previously issued internal admission.

    The value is stored verbatim: no trimming, lowercasing, or normalization.
    The object carries nothing else — it references admission state that lives
    entirely inside Liquent and is never supplied by an external caller.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("admission id must not be empty")
