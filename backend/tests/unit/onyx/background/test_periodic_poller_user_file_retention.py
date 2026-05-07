from datetime import datetime
from datetime import timedelta
from datetime import timezone
from types import SimpleNamespace
from uuid import uuid4

from onyx.background.periodic_poller import (
    select_user_file_ids_for_retention_cleanup,
)


class _Query:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def outerjoin(self, *_args, **_kwargs) -> "_Query":
        return self

    def filter(self, *_args, **_kwargs) -> "_Query":
        return self

    def order_by(self, *_args, **_kwargs) -> "_Query":
        return self

    def all(self) -> list[SimpleNamespace]:
        return self._rows


class _Session:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def query(self, *_args, **_kwargs) -> _Query:
        return _Query(self._rows)


def _row(*, age_days: int, size: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        created_at=datetime.now(timezone.utc) - timedelta(days=age_days),
        file_size=size,
    )


def test_retention_cleanup_selects_files_older_than_retention_window() -> None:
    now = datetime.now(timezone.utc)
    old_file = _row(age_days=8, size=100)
    recent_file = _row(age_days=2, size=100)

    selected = select_user_file_ids_for_retention_cleanup(
        db_session=_Session([old_file, recent_file]),
        retention_days=7,
        max_total_bytes=2_000,
        target_total_bytes=1_000,
        now=now,
    )

    assert selected == [old_file.id]


def test_retention_cleanup_leaves_recent_files_when_under_size_limit() -> None:
    now = datetime.now(timezone.utc)
    first = _row(age_days=1, size=400)
    second = _row(age_days=2, size=500)

    selected = select_user_file_ids_for_retention_cleanup(
        db_session=_Session([second, first]),
        retention_days=7,
        max_total_bytes=2_000,
        target_total_bytes=1_000,
        now=now,
    )

    assert selected == []


def test_retention_cleanup_deletes_oldest_recent_files_until_target_size() -> None:
    now = datetime.now(timezone.utc)
    oldest = _row(age_days=6, size=800)
    middle = _row(age_days=5, size=700)
    newest = _row(age_days=1, size=700)

    selected = select_user_file_ids_for_retention_cleanup(
        db_session=_Session([oldest, middle, newest]),
        retention_days=7,
        max_total_bytes=2_000,
        target_total_bytes=1_000,
        now=now,
    )

    assert selected == [oldest.id, middle.id]


def test_retention_cleanup_applies_age_rule_before_size_rule() -> None:
    now = datetime.now(timezone.utc)
    expired = _row(age_days=10, size=1_500)
    oldest_recent = _row(age_days=6, size=800)
    newest_recent = _row(age_days=1, size=800)

    selected = select_user_file_ids_for_retention_cleanup(
        db_session=_Session([expired, oldest_recent, newest_recent]),
        retention_days=7,
        max_total_bytes=1_000,
        target_total_bytes=700,
        now=now,
    )

    assert selected == [expired.id, oldest_recent.id, newest_recent.id]
