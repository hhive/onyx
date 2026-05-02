from sqlalchemy.orm import Session

from onyx.db.sub2api_user_credentials import get_sub2api_credential_for_user
from onyx.db.sub2api_user_credentials import upsert_sub2api_credential_for_user
from onyx.server.sub2api.models import Sub2APICredentialPayload
from tests.external_dependency_unit.conftest import create_test_user


def _credential(api_key: str) -> Sub2APICredentialPayload:
    return Sub2APICredentialPayload(
        api_key_id=11,
        api_key=api_key,
        api_base_url="https://sub2api.example.com/v1",
        text_model_name="gpt-5.5",
        image_model_name="gpt-image-2",
    )


def test_upsert_sub2api_credential_for_user_replaces_existing_key(
    db_session: Session,
) -> None:
    user = create_test_user(db_session, "sub2api_credential")

    first = upsert_sub2api_credential_for_user(db_session, user, _credential("sk-old"))
    second = upsert_sub2api_credential_for_user(db_session, user, _credential("sk-new"))

    db_session.flush()
    db_session.expire_all()

    stored = get_sub2api_credential_for_user(db_session, user.id)

    assert stored is not None
    assert first.id == second.id == stored.id
    assert stored.api_key.get_value(apply_mask=False) == "sk-new"
    assert stored.api_base_url == "https://sub2api.example.com/v1"
    assert stored.text_model_name == "gpt-5.5"
    assert stored.image_model_name == "gpt-image-2"

    db_session.rollback()
