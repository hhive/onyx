from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from onyx.db.models import Sub2APIUserCredential


@dataclass
class Sub2APIUserCredentialRecord:
    user_id: UUID
    sub2api_user_id: int
    api_key: str


class _CredentialSession(Protocol):
    def scalar(self, statement: object) -> Sub2APIUserCredentialRecord | None: ...

    def add(self, row: Sub2APIUserCredentialRecord) -> None: ...


def get_sub2api_user_credentials(
    db_session: Session, user_id: UUID
) -> Sub2APIUserCredential | None:
    return db_session.scalar(
        select(Sub2APIUserCredential).where(Sub2APIUserCredential.user_id == user_id)
    )


def upsert_sub2api_user_credentials(
    db_session: Session | _CredentialSession,
    *,
    user_id: UUID,
    sub2api_user_id: int,
    api_key: str,
) -> Sub2APIUserCredential | Sub2APIUserCredentialRecord:
    existing = db_session.scalar(
        select(Sub2APIUserCredential).where(Sub2APIUserCredential.user_id == user_id)
    )
    if existing is None:
        row: Sub2APIUserCredential | Sub2APIUserCredentialRecord
        if isinstance(db_session, Session):
            row = Sub2APIUserCredential(
                user_id=user_id,
                sub2api_user_id=sub2api_user_id,
                api_key=api_key,
            )
        else:
            row = Sub2APIUserCredentialRecord(
                user_id=user_id,
                sub2api_user_id=sub2api_user_id,
                api_key=api_key,
            )
        db_session.add(row)
        return row

    existing.sub2api_user_id = sub2api_user_id
    existing.api_key = api_key
    return existing
