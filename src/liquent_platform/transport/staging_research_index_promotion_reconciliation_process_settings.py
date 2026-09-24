"""Closed process settings for one-shot staging promotion reconciliation."""

from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.engine import make_url


class StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable(
    Exception
):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_reconciliation_process_settings_unavailable"
        )


@dataclass(frozen=True, slots=True)
class StagingResearchIndexPromotionReconciliationProcessSettings:
    provider_settings_file: Path
    database_url: str = field(repr=False)

    @classmethod
    def from_mapping(
        cls, values: dict[str, str]
    ) -> "StagingResearchIndexPromotionReconciliationProcessSettings":
        try:
            if type(values) is not dict or set(values) != {
                "provider_settings_file",
                "database_url",
            }:
                raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
            if any(type(value) is not str for value in values.values()):
                raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
            raw_path = values["provider_settings_file"]
            path = Path(raw_path)
            if (
                not path.is_absolute()
                or path == Path("/")
                or ".." in path.parts
                or str(path) != raw_path
                or len(raw_path) > 4096
            ):
                raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
            database_url = values["database_url"]
            if not database_url or len(database_url) > 4096:
                raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
            url = make_url(database_url)
            if url.drivername not in {
                "sqlite",
                "sqlite+pysqlite",
                "postgresql+psycopg",
            }:
                raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
            if url.get_backend_name() == "sqlite" and any(
                value is not None
                for value in (url.username, url.password, url.host, url.port)
            ):
                raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
            return cls(path, database_url)
        except StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable from None

    def __repr__(self) -> str:
        return "StagingResearchIndexPromotionReconciliationProcessSettings()"
