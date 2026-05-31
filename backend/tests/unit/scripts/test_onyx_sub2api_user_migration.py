from scripts.onyx_sub2api_user_migration import MigrationInputUser
from scripts.onyx_sub2api_user_migration import migrate_users


def test_dry_run_reports_migration_without_writing() -> None:
    rows = [
        {
            "id": "user-1",
            "email": "sub2api-1@sub2api.local",
            "role": "basic",
            "sub2api_user_id": None,
            "api_key": None,
        }
    ]

    report = migrate_users(
        rows,
        [
            MigrationInputUser(
                sub2api_user_id=1,
                old_email="sub2api-1@sub2api.local",
                email="admin@example.com",
                role="admin",
                api_key="sk-test",
            )
        ],
        apply=False,
    )

    assert report.summary["migrated"] == 1
    assert rows[0]["email"] == "sub2api-1@sub2api.local"
    assert report.migrated[0]["new_email"] == "admin@example.com"


def test_apply_updates_existing_old_email_user_and_credentials() -> None:
    rows = [
        {
            "id": "user-1",
            "email": "sub2api-1@sub2api.local",
            "role": "basic",
            "sub2api_user_id": None,
            "api_key": None,
        }
    ]

    report = migrate_users(
        rows,
        [
            MigrationInputUser(
                sub2api_user_id=1,
                old_email="sub2api-1@sub2api.local",
                email="admin@example.com",
                role="admin",
                api_key="sk-test",
            )
        ],
        apply=True,
    )

    assert report.summary["migrated"] == 1
    assert rows[0]["email"] == "admin@example.com"
    assert rows[0]["role"] == "admin"
    assert rows[0]["sub2api_user_id"] == 1
    assert rows[0]["api_key"] == "sk-test"


def test_conflict_when_target_email_belongs_to_different_user() -> None:
    rows = [
        {
            "id": "old-user",
            "email": "sub2api-1@sub2api.local",
            "role": "basic",
            "sub2api_user_id": None,
            "api_key": None,
        },
        {
            "id": "real-user",
            "email": "admin@example.com",
            "role": "basic",
            "sub2api_user_id": None,
            "api_key": None,
        },
    ]

    report = migrate_users(
        rows,
        [
            MigrationInputUser(
                sub2api_user_id=1,
                old_email="sub2api-1@sub2api.local",
                email="admin@example.com",
                role="admin",
                api_key="sk-test",
            )
        ],
        apply=True,
    )

    assert report.summary["conflicts"] == 1
    assert rows[0]["email"] == "sub2api-1@sub2api.local"
    assert report.conflicts[0]["reason"] == "target_email_exists"
