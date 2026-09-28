import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError


pytestmark = pytest.mark.postgres_integration


def test_release_registry_foundation_is_empty_and_enforces_key_assignment(
    postgres_engine: Engine,
) -> None:
    tables = set(inspect(postgres_engine).get_table_names())
    assert {
        "release_signer_authorities",
        "release_registry_lifecycle_authorities",
        "release_signing_keys",
        "release_registry_set_revisions",
        "release_registry_revision_signers",
        "release_registry_revision_lifecycle_authorities",
        "release_registry_revision_keys",
        "release_registry_current_set",
        "release_registry_lifecycle_changes",
        "release_signing_decisions",
    } <= tables
    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM release_registry_set_revisions"
        )) == 0
        assert connection.scalar(text(
            "SELECT count(*) FROM release_signing_decisions"
        )) == 0

    with postgres_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO release_signer_authorities VALUES "
            "(decode('61','hex')),(decode('62','hex'))"
        ))
        connection.execute(text(
            "INSERT INTO release_signing_keys VALUES "
            "(decode('31','hex'),decode('61','hex'),'ssh-ed25519',"
            "'liquent-operations-release-v1','SHA256:one','ssh-ed25519 ONE')"
        ))
        connection.execute(text(
            "INSERT INTO release_registry_set_revisions VALUES "
            "(decode('72','hex'),decode('70','hex'),'active')"
        ))
        connection.execute(text(
            "INSERT INTO release_registry_revision_keys VALUES "
            "(decode('72','hex'),decode('31','hex'),decode('61','hex'),'inactive')"
        ))

    with pytest.raises(IntegrityError):
        with postgres_engine.begin() as connection:
            connection.execute(text(
                "UPDATE release_signing_keys SET signer_authority_id=decode('62','hex') "
                "WHERE key_id=decode('31','hex')"
            ))
