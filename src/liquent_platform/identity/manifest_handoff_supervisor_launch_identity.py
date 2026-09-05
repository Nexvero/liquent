"""Closed numeric identity policy shared by launch file and wrapper."""

from dataclasses import dataclass, field


_MAX_ID = 2_147_483_647


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorLaunchIdentityPolicy:
    host_owner_uid: int = field(repr=False)
    reader_gid: int = field(repr=False)
    wrapper_uid: int = field(repr=False)
    wrapper_gid: int = field(repr=False)

    def __post_init__(self) -> None:
        values = (
            self.host_owner_uid, self.reader_gid, self.wrapper_uid, self.wrapper_gid
        )
        if (
            any(type(value) is not int or not 1 <= value <= _MAX_ID for value in values)
            or self.wrapper_gid != self.reader_gid
            or self.wrapper_uid == self.host_owner_uid
        ):
            raise ValueError("manifest handoff supervisor launch identity policy is invalid")

    @property
    def docker_user(self) -> str:
        return f"{self.wrapper_uid}:{self.wrapper_gid}"
