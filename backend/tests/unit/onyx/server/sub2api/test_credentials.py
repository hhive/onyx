from uuid import uuid4

from onyx.db.sub2api_user_credentials import Sub2APIUserCredentialRecord
from onyx.db.sub2api_user_credentials import upsert_sub2api_user_credentials


class _FakeSession:
    def __init__(self, existing: Sub2APIUserCredentialRecord | None = None) -> None:
        self.existing = existing
        self.added: list[Sub2APIUserCredentialRecord] = []

    def scalar(self, _stmt: object) -> Sub2APIUserCredentialRecord | None:
        return self.existing

    def add(self, row: Sub2APIUserCredentialRecord) -> None:
        self.added.append(row)


def test_upsert_creates_user_credentials_without_api_base() -> None:
    user_id = uuid4()
    session = _FakeSession()

    row = upsert_sub2api_user_credentials(
        db_session=session,  # type: ignore[arg-type]
        user_id=user_id,
        sub2api_user_id=42,
        api_key="sk-test",
    )

    assert row.user_id == user_id
    assert row.sub2api_user_id == 42
    assert row.api_key == "sk-test"
    assert not hasattr(row, "api_base_url")
    assert not hasattr(row, "default_text_model")
    assert not hasattr(row, "default_image_model")
    assert session.added == [row]


def test_upsert_updates_existing_credentials() -> None:
    existing = Sub2APIUserCredentialRecord(
        user_id=uuid4(),
        sub2api_user_id=1,
        api_key="old-key",
    )
    session = _FakeSession(existing)

    row = upsert_sub2api_user_credentials(
        db_session=session,  # type: ignore[arg-type]
        user_id=existing.user_id,
        sub2api_user_id=2,
        api_key="new-key",
    )

    assert row is existing
    assert row.sub2api_user_id == 2
    assert row.api_key == "new-key"
    assert session.added == []
