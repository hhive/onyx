import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session


VALID_ROLES = {"admin", "basic", "curator", "global_curator", "limited", "user"}


@dataclass(frozen=True)
class MigrationInputUser:
    sub2api_user_id: int
    old_email: str
    email: str
    role: str
    api_key: str


@dataclass
class MigrationReport:
    migrated: list[dict[str, Any]]
    skipped: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    summary: dict[str, Any]


def _normalize_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized == "user":
        return "basic"
    return normalized


def _build_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["email"]).lower(): row for row in rows}


def _role_value(role: Any) -> str:
    return str(getattr(role, "value", role))


def migrate_users(
    rows: list[dict[str, Any]],
    input_users: list[MigrationInputUser],
    *,
    apply: bool,
) -> MigrationReport:
    migrated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    users_by_email = _build_index(rows)

    for input_user in input_users:
        try:
            old_email = input_user.old_email.strip().lower()
            new_email = input_user.email.strip().lower()
            role = _normalize_role(input_user.role)

            if not input_user.api_key:
                errors.append(
                    {
                        "sub2api_user_id": input_user.sub2api_user_id,
                        "email": input_user.email,
                        "error": "api_key_required",
                    }
                )
                continue

            if role not in VALID_ROLES:
                errors.append(
                    {
                        "sub2api_user_id": input_user.sub2api_user_id,
                        "email": input_user.email,
                        "error": "invalid_role",
                    }
                )
                continue

            old_row = users_by_email.get(old_email)
            if old_row is None:
                skipped.append(
                    {
                        "sub2api_user_id": input_user.sub2api_user_id,
                        "email": input_user.email,
                        "reason": "old_email_not_found",
                    }
                )
                continue

            target_row = users_by_email.get(new_email)
            if target_row is not None and target_row["id"] != old_row["id"]:
                conflicts.append(
                    {
                        "sub2api_user_id": input_user.sub2api_user_id,
                        "old_email": old_email,
                        "new_email": new_email,
                        "existing_onyx_user_id": target_row["id"],
                        "matched_onyx_user_id": old_row["id"],
                        "reason": "target_email_exists",
                    }
                )
                continue

            migrated_row = {
                "sub2api_user_id": input_user.sub2api_user_id,
                "onyx_user_id": str(old_row["id"]),
                "old_email": old_email,
                "new_email": new_email,
                "old_role": _role_value(old_row["role"]),
                "new_role": role,
                "status": "applied" if apply else "dry_run",
            }
            migrated.append(migrated_row)

            if apply:
                old_row["email"] = new_email
                old_row["role"] = role
                old_row["sub2api_user_id"] = input_user.sub2api_user_id
                old_row["api_key"] = input_user.api_key
                users_by_email.pop(old_email, None)
                users_by_email[new_email] = old_row

        except Exception as e:
            errors.append(
                {
                    "sub2api_user_id": input_user.sub2api_user_id,
                    "email": input_user.email,
                    "error": str(e),
                }
            )

    summary = {
        "total": len(input_users),
        "migrated": len(migrated),
        "skipped": len(skipped),
        "conflicts": len(conflicts),
        "errors": len(errors),
        "apply": apply,
    }
    return MigrationReport(migrated, skipped, conflicts, errors, summary)


def load_onyx_user_rows(db_session: Session) -> list[dict[str, Any]]:
    from onyx.db.models import User

    rows: list[dict[str, Any]] = []
    for user_id, email, role in db_session.execute(select(User.id, User.email, User.role)):
        rows.append(
            {
                "id": user_id,
                "email": email,
                "role": role,
            }
        )
    return rows


def apply_report_to_db(
    db_session: Session,
    report: MigrationReport,
    input_users: list[MigrationInputUser],
) -> None:
    from onyx.auth.schemas import UserRole
    from onyx.db.models import User
    from onyx.db.sub2api_user_credentials import upsert_sub2api_user_credentials

    input_by_sub2api_id = {user.sub2api_user_id: user for user in input_users}

    for migrated in report.migrated:
        input_user = input_by_sub2api_id[migrated["sub2api_user_id"]]
        user = db_session.scalar(
            select(User).where(User.id == UUID(migrated["onyx_user_id"]))
        )
        if user is None:
            raise RuntimeError(f"Onyx user not found: {migrated['onyx_user_id']}")

        user.email = migrated["new_email"]
        user.role = UserRole(migrated["new_role"])
        upsert_sub2api_user_credentials(
            db_session,
            user_id=user.id,
            sub2api_user_id=input_user.sub2api_user_id,
            api_key=input_user.api_key,
        )


def _load_input_users(path: Path) -> list[MigrationInputUser]:
    raw_users = json.loads(path.read_text(encoding="utf-8"))
    return [MigrationInputUser(**raw_user) for raw_user in raw_users]


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(report: MigrationReport, report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(
        report_dir / "migrated.csv",
        report.migrated,
        [
            "sub2api_user_id",
            "onyx_user_id",
            "old_email",
            "new_email",
            "old_role",
            "new_role",
            "status",
        ],
    )
    _write_csv(
        report_dir / "skipped.csv",
        report.skipped,
        ["sub2api_user_id", "email", "reason"],
    )
    _write_csv(
        report_dir / "conflicts.csv",
        report.conflicts,
        [
            "sub2api_user_id",
            "old_email",
            "new_email",
            "existing_onyx_user_id",
            "matched_onyx_user_id",
            "reason",
        ],
    )
    _write_csv(
        report_dir / "errors.csv",
        report.errors,
        ["sub2api_user_id", "email", "error"],
    )
    (report_dir / "summary.json").write_text(
        json.dumps(report.summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare Sub2API synthetic-email Onyx user migration reports."
    )
    parser.add_argument("--sub2api-users-json", required=True)
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.dry_run == args.apply:
        raise SystemExit("Pass exactly one of --dry-run or --apply")

    from onyx.db.engine.sql_engine import get_session_with_current_tenant
    from onyx.db.engine.sql_engine import SqlEngine

    input_users = _load_input_users(Path(args.sub2api_users_json))
    SqlEngine.init_engine(pool_size=1, max_overflow=0, app_name="sub2api_user_migration")

    try:
        with get_session_with_current_tenant() as db_session:
            rows = load_onyx_user_rows(db_session)
            report = migrate_users(rows, input_users, apply=args.apply)
            write_report(report, Path(args.report_dir))

            if args.apply:
                if report.summary["conflicts"] or report.summary["errors"]:
                    db_session.rollback()
                    return 1
                apply_report_to_db(db_session, report, input_users)
                db_session.commit()
    finally:
        SqlEngine.reset_engine()

    return 0 if report.summary["conflicts"] == 0 and report.summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
