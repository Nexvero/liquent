"""Append-only persistence for staging promotion evidence bindings."""

from datetime import datetime

from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceRun,
)
from liquent_platform.application.staging_research_index_promotion_evidence import (
    StagingResearchIndexPromotionEvidenceBinding,
)


_INSERT = text(
    "INSERT INTO staging_research_index_promotion_evidence"
    " (evidence_digest,candidate_digest,staging_origin,observed_at)"
    " VALUES (:evidence,:candidate,:origin,:observed)"
)
_SELECT = text(
    "SELECT evidence_digest,candidate_digest,staging_origin,observed_at"
    " FROM staging_research_index_promotion_evidence"
    " WHERE evidence_digest=:evidence"
)


class StagingResearchIndexPromotionEvidenceStoreUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_evidence_store_unavailable")


class DatabaseStagingResearchIndexPromotionEvidence:
    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseStagingResearchIndexPromotionEvidence()"

    def record(
        self, binding: StagingResearchIndexPromotionEvidenceBinding
    ) -> StagingResearchIndexPromotionEvidenceBinding:
        if type(binding) is not StagingResearchIndexPromotionEvidenceBinding:
            raise StagingResearchIndexPromotionEvidenceStoreUnavailable
        values = {
            "evidence": binding.evidence_digest,
            "candidate": binding.run.candidate_digest,
            "origin": binding.run.staging_origin,
            "observed": binding.run.observed_at.isoformat().replace("+00:00", "Z"),
        }
        try:
            try:
                with self._engine.begin() as connection:
                    connection.execute(_INSERT, values)
                return binding
            except IntegrityError:
                with self._engine.connect() as connection:
                    row = connection.execute(
                        _SELECT, {"evidence": binding.evidence_digest}
                    ).mappings().one_or_none()
                if row is None or (
                    row["evidence_digest"] != values["evidence"]
                    or row["candidate_digest"] != values["candidate"]
                    or row["staging_origin"] != values["origin"]
                    or row["observed_at"] != values["observed"]
                ):
                    raise StagingResearchIndexPromotionEvidenceStoreUnavailable
                return binding
        except StagingResearchIndexPromotionEvidenceStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionEvidenceStoreUnavailable from None

    def resolve(self, evidence_digest: str):
        try:
            if (
                type(evidence_digest) is not str
                or len(evidence_digest) != 71
                or not evidence_digest.startswith("sha256:")
            ):
                raise StagingResearchIndexPromotionEvidenceStoreUnavailable
            with self._engine.connect() as connection:
                row = connection.execute(
                    _SELECT, {"evidence": evidence_digest}
                ).mappings().one_or_none()
            if row is None:
                return None
            run = StagingResearchIndexAcceptanceRun(
                row["candidate_digest"],
                row["staging_origin"],
                datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00")),
            )
            return StagingResearchIndexPromotionEvidenceBinding(
                run, row["evidence_digest"]
            )
        except StagingResearchIndexPromotionEvidenceStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionEvidenceStoreUnavailable from None
