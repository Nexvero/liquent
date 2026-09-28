"""Closed immutable digest anchor for one supervisor launch document."""

from dataclasses import dataclass, field
import re


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorLaunchDocumentDigest:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.value) is not str or re.fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ValueError("manifest handoff supervisor launch document digest is invalid")
