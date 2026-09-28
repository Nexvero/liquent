"""Closed settings value for the promotion provider status endpoint."""

from dataclasses import dataclass, field
from urllib.parse import urlsplit


class StagingResearchIndexPromotionProviderSettingsUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_provider_settings_unavailable")


@dataclass(frozen=True, slots=True)
class StagingResearchIndexPromotionProviderSettings:
    endpoint: str = field(repr=False)

    @classmethod
    def from_mapping(
        cls, values: dict[str, str]
    ) -> "StagingResearchIndexPromotionProviderSettings":
        try:
            if (
                type(values) is not dict
                or set(values) != {"endpoint"}
                or type(values["endpoint"]) is not str
            ):
                raise StagingResearchIndexPromotionProviderSettingsUnavailable
            endpoint = values["endpoint"]
            parsed = urlsplit(endpoint)
            if (
                parsed.scheme != "https"
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
                or not parsed.path.endswith("/")
                or len(endpoint) > 2048
            ):
                raise StagingResearchIndexPromotionProviderSettingsUnavailable
            return cls(endpoint)
        except StagingResearchIndexPromotionProviderSettingsUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionProviderSettingsUnavailable from None

    def __repr__(self) -> str:
        return "StagingResearchIndexPromotionProviderSettings()"
