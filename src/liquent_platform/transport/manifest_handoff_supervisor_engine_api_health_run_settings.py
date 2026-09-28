"""Closed run settings for the private Engine API health server."""

from __future__ import annotations

from dataclasses import dataclass

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiHealthRunSettings:
    maximum_exchanges: int

    @classmethod
    def from_mapping(cls, values: dict[str, str]):
        try:
            if type(values) is not dict or set(values) != {"maximum_exchanges"}:
                raise ManifestHandoffRegistryUnavailable
            raw = values["maximum_exchanges"]
            if (type(raw) is not str or not raw or not raw.isascii()
                    or not raw.isdigit() or (len(raw) > 1 and raw[0] == "0")):
                raise ManifestHandoffRegistryUnavailable
            return cls(int(raw))
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def __post_init__(self) -> None:
        if (type(self.maximum_exchanges) is not int
                or self.maximum_exchanges < 1
                or self.maximum_exchanges > 1_000_000):
            raise ManifestHandoffRegistryUnavailable

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorEngineApiHealthRunSettings()"
