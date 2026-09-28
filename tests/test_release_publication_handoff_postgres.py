from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_publication import (
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationDecisionId,
    ReleasePublicationHandoffId,
    ReleasePublisherAuthorityId,
)
from liquent_platform.persistence.release_publication_handoff import (
    DatabaseAuthorizedReleasePublicationHandoff,
)
from test_release_promotion_verifier import (
    AUTHORITY_ID,
    KEY_ID,
    RegistryProjection,
    signed_candidate,
)
from tools.release_promotion_verifier import verify_release_promotion_with_projection


pytestmark = pytest.mark.postgres_integration


def test_postgresql_commits_current_authority_bound_handoff_without_receipt(
    postgres_engine: Engine, signed_candidate: dict[str, object], tmp_path: Path,
):
    registry = signed_candidate["registry"].read_bytes()
    projection = RegistryProjection(registry)
    evidence = verify_release_promotion_with_projection(
        bundle_path=signed_candidate["bundle"],
        signature_path=signed_candidate["signature"],
        registry_projection=projection,
        key_id=KEY_ID,
        clock=lambda: datetime(2026, 8, 18, 14, tzinfo=timezone.utc),
    )
    evidence_path = tmp_path / "promotion.json"
    evidence_path.write_text(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n"
    )
    with postgres_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO release_signer_authorities VALUES (:signer);"
        ), {"signer": AUTHORITY_ID.encode()})
        connection.execute(text(
            "INSERT INTO release_signing_keys VALUES "
            "(:key,:signer,'ssh-ed25519','liquent-operations-release-v1',"
            ":fingerprint,:public_key)"
        ), {"key": KEY_ID.encode(), "signer": AUTHORITY_ID.encode(),
            "fingerprint": signed_candidate["fingerprint"],
            "public_key": signed_candidate["public_key"]})
        connection.execute(text(
            "INSERT INTO release_registry_set_revisions VALUES "
            "(:revision,:policy,'active')"
        ), {"revision": b"release-revision-251", "policy": b"release-policy:1"})
        connection.execute(text(
            "INSERT INTO release_registry_revision_signers VALUES "
            "(:revision,:signer,'active')"
        ), {"revision": b"release-revision-251", "signer": AUTHORITY_ID.encode()})
        connection.execute(text(
            "INSERT INTO release_registry_revision_keys VALUES "
            "(:revision,:key,:signer,'active')"
        ), {"revision": b"release-revision-251", "key": KEY_ID.encode(),
            "signer": AUTHORITY_ID.encode()})
        connection.execute(text(
            "INSERT INTO release_registry_current_set VALUES (1,:revision)"
        ), {"revision": b"release-revision-251"})
        connection.execute(text(
            "INSERT INTO release_publication_channels VALUES (:channel)"
        ), {"channel": b"channel-251"})
        connection.execute(text(
            "INSERT INTO release_publisher_authorities VALUES (:publisher)"
        ), {"publisher": b"publisher-251"})
        connection.execute(text(
            "INSERT INTO release_publication_channel_revisions VALUES "
            "(:revision,:channel,'active','operational_bundle','liquent',"
            "'package-index','stable')"
        ), {"revision": b"channel-revision-251", "channel": b"channel-251"})
        connection.execute(text(
            "INSERT INTO release_publication_revision_publishers VALUES "
            "(:revision,:channel,:publisher,'active')"
        ), {"revision": b"channel-revision-251", "channel": b"channel-251",
            "publisher": b"publisher-251"})
        connection.execute(text(
            "INSERT INTO release_publication_current_channels VALUES "
            "(:channel,:revision)"
        ), {"channel": b"channel-251", "revision": b"channel-revision-251"})
    result = DatabaseAuthorizedReleasePublicationHandoff(
        postgres_engine, registry_projection=RegistryProjection(registry),
        clock=lambda: datetime(2026, 8, 18, 15, tzinfo=timezone.utc),
    ).accept_handoff(
        ReleasePublicationHandoffId("handoff-251"),
        ReleasePublicationDecisionId("decision-251"),
        ReleasePublisherAuthorityId("publisher-251"),
        ReleasePublicationChannelId("channel-251"),
        ReleasePublicationChannelPolicyRevisionId("channel-revision-251"),
        str(signed_candidate["bundle"]), str(signed_candidate["signature"]),
        str(evidence_path),
    )
    assert result is not None
    with postgres_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT (SELECT count(*) FROM release_publication_handoffs),"
            "(SELECT count(*) FROM release_publication_receipts)"
        )).one() == (1, 0)
