"""The durable external identity key produced by an outer authentication boundary."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExternalIdentity:
    """A verified ``(issuer, subject)`` pair, treated exactly and opaquely.

    Both values are stored verbatim. There is no lowercasing, no slash trimming,
    and no email normalization: two identities are equal only when both fields
    match byte for byte. The object carries nothing else — no email, claims,
    tokens, roles, or session material.
    """

    issuer: str
    subject: str

    def __post_init__(self) -> None:
        if not self.issuer:
            raise ValueError("issuer must not be empty")
        if not self.subject:
            raise ValueError("subject must not be empty")
