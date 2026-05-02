from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from onyx.db.models import Sub2APIUserCredential
from onyx.db.models import User
from onyx.server.sub2api.models import Sub2APICredentialPayload


def get_sub2api_credential_for_user(
    db_session: Session,
    user_id: UUID | str,
) -> Sub2APIUserCredential | None:
    return db_session.scalar(
        select(Sub2APIUserCredential).where(
            Sub2APIUserCredential.user_id == user_id,
        )
    )


def upsert_sub2api_credential_for_user(
    db_session: Session,
    user: User,
    credential: Sub2APICredentialPayload,
    *,
    sub2api_user_id: int = 0,
) -> Sub2APIUserCredential:
    existing = get_sub2api_credential_for_user(db_session, user.id)
    if existing is None:
        existing = Sub2APIUserCredential(
            user_id=user.id,
            sub2api_user_id=sub2api_user_id,
            api_key_id=credential.api_key_id,
            api_key=credential.api_key,
            api_base_url=credential.api_base_url,
            text_model_name=credential.text_model_name,
            image_model_name=credential.image_model_name,
        )
        db_session.add(existing)
        db_session.flush()
        return existing

    existing.sub2api_user_id = sub2api_user_id
    existing.api_key_id = credential.api_key_id
    existing.api_key = credential.api_key
    existing.api_base_url = credential.api_base_url
    existing.text_model_name = credential.text_model_name
    existing.image_model_name = credential.image_model_name
    db_session.flush()
    return existing


def delete_sub2api_credential_for_user(
    db_session: Session,
    user_id: UUID | str,
) -> None:
    existing = get_sub2api_credential_for_user(db_session, user_id)
    if existing is not None:
        db_session.delete(existing)
        db_session.flush()
