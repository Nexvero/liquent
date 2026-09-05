"""One-time atomic bootstrap of the publication control plane."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.release_publication import (
    BootstrappedReleasePublicationControlPlane,
    ReleasePublicationBootstrapId,
    ReleasePublicationChannelDefinition,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublisherAuthorityId,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationBootstrapConflict,
    ReleasePublicationBootstrapUnavailable,
)


_TABLES = (
    "release_publication_channels", "release_publisher_authorities",
    "release_publication_channel_revisions",
    "release_publication_revision_publishers",
    "release_publication_current_channels", "release_publication_handoffs",
    "release_publication_receipts", "release_publication_reassessments",
    "release_publication_bootstraps",
)
_LOCK = text("LOCK TABLE " + ", ".join(_TABLES) + " IN SHARE ROW EXCLUSIVE MODE")
_HAS_INVENTORY = text("SELECT " + " OR ".join(
    f"EXISTS (SELECT 1 FROM {table})" for table in _TABLES
))
_EXISTING = text(
    "SELECT bootstrap.publisher_authority_id,bootstrap.channel_id,"
    " bootstrap.channel_revision_id,bootstrap.package_name,"
    " bootstrap.provider_kind,bootstrap.target_name,revision.status,"
    " revision.artifact_class,publisher.status AS publisher_status"
    " FROM release_publication_bootstraps AS bootstrap"
    " JOIN release_publication_channel_revisions AS revision"
    " ON revision.revision_id=bootstrap.channel_revision_id"
    " AND revision.channel_id=bootstrap.channel_id"
    " JOIN release_publication_revision_publishers AS publisher"
    " ON publisher.revision_id=bootstrap.channel_revision_id"
    " AND publisher.channel_id=bootstrap.channel_id"
    " AND publisher.authority_id=bootstrap.publisher_authority_id"
    " JOIN release_publication_current_channels AS current"
    " ON current.channel_id=bootstrap.channel_id"
    " AND current.revision_id=bootstrap.channel_revision_id"
    " WHERE bootstrap.bootstrap_id=:bootstrap"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise ReleasePublicationBootstrapUnavailable
    return value.encode()


def _decode(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ReleasePublicationBootstrapUnavailable
    return bytes(value).decode()


class DatabaseInitialReleasePublicationControlPlaneBootstrap:
    __slots__ = ("_engine", "_publisher", "_channel", "_revision")

    def __init__(
        self, engine: Engine, *,
        generate_publisher_authority_id: Callable[[], ReleasePublisherAuthorityId],
        generate_channel_id: Callable[[], ReleasePublicationChannelId],
        generate_channel_revision_id: Callable[
            [], ReleasePublicationChannelPolicyRevisionId
        ],
    ) -> None:
        self._engine = engine
        self._publisher = generate_publisher_authority_id
        self._channel = generate_channel_id
        self._revision = generate_channel_revision_id

    def __repr__(self) -> str:
        return "DatabaseInitialReleasePublicationControlPlaneBootstrap()"

    def bootstrap(self, bootstrap_id, channel):
        try:
            if type(bootstrap_id) is not ReleasePublicationBootstrapId:
                raise ReleasePublicationBootstrapUnavailable
            if type(channel) is not ReleasePublicationChannelDefinition:
                raise ReleasePublicationBootstrapUnavailable
            values = {"bootstrap": _encode(bootstrap_id.value)}
            with self._engine.begin() as transaction:
                return self._bootstrap(transaction, bootstrap_id, channel, values)
        except (ReleasePublicationBootstrapConflict,
                ReleasePublicationBootstrapUnavailable) as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleasePublicationBootstrapUnavailable

    def _bootstrap(self, transaction: Connection, bootstrap_id, definition, values):
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK)
        elif transaction.dialect.name != "sqlite":
            raise ReleasePublicationBootstrapUnavailable
        existing = transaction.execute(_EXISTING, values).first()
        if existing is not None:
            return self._resolve(bootstrap_id, definition, existing)
        if transaction.scalar(_HAS_INVENTORY):
            return None
        publisher = self._publisher()
        channel = self._channel()
        revision = self._revision()
        if type(publisher) is not ReleasePublisherAuthorityId:
            raise ReleasePublicationBootstrapUnavailable
        if type(channel) is not ReleasePublicationChannelId:
            raise ReleasePublicationBootstrapUnavailable
        if type(revision) is not ReleasePublicationChannelPolicyRevisionId:
            raise ReleasePublicationBootstrapUnavailable
        values.update({
            "publisher": _encode(publisher.value), "channel": _encode(channel.value),
            "revision": _encode(revision.value), "package": definition.package_name,
            "provider": definition.provider_kind, "target": definition.target_name,
        })
        transaction.execute(text(
            "INSERT INTO release_publication_channels VALUES (:channel)"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_publisher_authorities VALUES (:publisher)"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_publication_channel_revisions VALUES "
            "(:revision,:channel,'active','operational_bundle',:package,:provider,:target)"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_publication_revision_publishers VALUES "
            "(:revision,:channel,:publisher,'active')"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_publication_current_channels VALUES "
            "(:channel,:revision)"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_publication_bootstraps VALUES "
            "(:bootstrap,:publisher,:channel,:revision,:package,:provider,:target)"
        ), values)
        return BootstrappedReleasePublicationControlPlane(
            bootstrap_id, publisher, channel, revision
        )

    @staticmethod
    def _resolve(bootstrap_id, definition, row):
        if (row.package_name != definition.package_name
            or row.provider_kind != definition.provider_kind
            or row.target_name != definition.target_name):
            raise ReleasePublicationBootstrapConflict
        if (row.status != "active" or row.publisher_status != "active"
            or row.artifact_class != "operational_bundle"):
            raise ReleasePublicationBootstrapUnavailable
        return BootstrappedReleasePublicationControlPlane(
            bootstrap_id,
            ReleasePublisherAuthorityId(_decode(row.publisher_authority_id)),
            ReleasePublicationChannelId(_decode(row.channel_id)),
            ReleasePublicationChannelPolicyRevisionId(
                _decode(row.channel_revision_id)
            ),
        )
