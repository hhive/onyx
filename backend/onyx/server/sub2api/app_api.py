import secrets
import uuid
from html import escape
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, Path, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi_users import exceptions
from fastapi_users.authentication import Strategy
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.auth.schemas import UserCreate
from onyx.auth.users import UserManager, auth_backend, current_user, get_user_manager
from onyx.configs.app_configs import (
    SUB2API_LAUNCH_ORIGIN,
    SUB2API_ONYX_REDIRECT_PATH,
    WEB_DOMAIN,
)
from onyx.configs.constants import FASTAPI_USERS_AUTH_COOKIE_NAME
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import AccountType
from onyx.db.models import Sub2APIUserCredential, User
from onyx.db.sub2api_user_credentials import (
    get_sub2api_credential_for_user,
    upsert_sub2api_credential_for_user,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.server.sub2api import app_client
from onyx.server.sub2api.api import _generate_secure_password
from onyx.server.sub2api.app_session import get_grant, revoke_session_grant, save_grant
from onyx.server.sub2api.models import (
    AppGrant,
    KeyModels,
    KeyPage,
    Sub2APICredentialPayload,
)

router = APIRouter(prefix="/sub2api")


def _https_origin(value: str) -> str | None:
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        return None
    if (
        parts.scheme != "https"
        or parts.hostname is None
        or parts.username is not None
        or parts.password is not None
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
    ):
        return None
    suffix = f":{port}" if port and port != 443 else ""
    return f"https://{parts.hostname}{suffix}"


def _launch_origins() -> list[str]:
    return [
        origin
        for value in SUB2API_LAUNCH_ORIGIN.split(",")
        if (origin := _https_origin(value.strip())) is not None
    ]


def valid_origin(headers: list[str], allowed_origin: str, web_domain: str) -> bool:
    source = _https_origin(allowed_origin)
    target = _https_origin(web_domain)
    if source is None or target is None or headers != [source]:
        return False
    source_host = urlsplit(source).hostname
    target_host = urlsplit(target).hostname
    assert source_host is not None and target_host is not None
    return source_host == target_host or target_host.endswith(f".{source_host}")


def _launch_form(ticket: str) -> HTMLResponse:
    nonce = secrets.token_urlsafe(24)
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Onyx</title>
<form method="post" action="/api/sub2api/launch/finish">
<input type="hidden" name="ticket" value="{escape(ticket, quote=True)}">
<noscript><button type="submit">Continue to Onyx</button></noscript>
</form>
<script nonce="{nonce}">document.forms[0].submit()</script>
</html>""",
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "same-origin",
            "Content-Security-Policy": (
                f"default-src 'none'; script-src 'nonce-{nonce}'; "
                "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
            ),
        },
    )


@router.get("/launch", include_in_schema=False)
async def recover_legacy_launch(request: Request) -> Response:
    origins = _launch_origins()
    headers = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
    if not origins:
        return Response(status_code=404, headers=headers)

    referer = request.headers.get("referer", "")
    origin = next(
        (
            candidate
            for candidate in origins
            if referer == candidate or referer.startswith(f"{candidate}/")
        ),
        origins[0],
    )
    return RedirectResponse(f"{origin}/keys", status_code=303, headers=headers)


@router.post("/launch")
async def launch(
    request: Request,
    ticket: Annotated[str, Form(min_length=1, max_length=512)],
    strategy: Strategy[User, uuid.UUID] = Depends(auth_backend.get_strategy),
    user_manager: UserManager = Depends(get_user_manager),
    db_session: Session = Depends(get_session),
) -> Response:
    origins = request.headers.getlist("origin")
    if (
        len(origins) != 1
        or origins[0] not in _launch_origins()
        or _https_origin(WEB_DOMAIN) is None
    ):
        raise OnyxError(OnyxErrorCode.UNAUTHORIZED, "Sub2API launch origin rejected.")
    if not valid_origin(origins, origins[0], WEB_DOMAIN):
        return _launch_form(ticket)
    return await _complete_launch(request, ticket, strategy, user_manager, db_session)


@router.post("/launch/finish")
async def finish_launch(
    request: Request,
    ticket: Annotated[str, Form(min_length=1, max_length=512)],
    strategy: Strategy[User, uuid.UUID] = Depends(auth_backend.get_strategy),
    user_manager: UserManager = Depends(get_user_manager),
    db_session: Session = Depends(get_session),
) -> RedirectResponse:
    origin = _https_origin(WEB_DOMAIN)
    if (
        not SUB2API_LAUNCH_ORIGIN
        or origin is None
        or request.headers.getlist("origin") != [origin]
    ):
        raise OnyxError(OnyxErrorCode.UNAUTHORIZED, "Sub2API launch origin rejected.")
    return await _complete_launch(request, ticket, strategy, user_manager, db_session)


async def _complete_launch(
    request: Request,
    ticket: str,
    strategy: Strategy[User, uuid.UUID],
    user_manager: UserManager,
    db_session: Session,
) -> RedirectResponse:
    existing_token = request.cookies.get(FASTAPI_USERS_AUTH_COOKIE_NAME)
    current = await strategy.read_token(existing_token, user_manager)
    exchange = await app_client.exchange(ticket)
    try:
        user = await _bound_user(
            exchange.user_id, exchange.email, current, user_manager, db_session
        )
        grant = AppGrant(user_id=exchange.user_id, grant_token=exchange.grant_token)
        session_token = await strategy.write_token(user)
        try:
            response = RedirectResponse(SUB2API_ONYX_REDIRECT_PATH, status_code=303)
            login_response = await auth_backend.transport.get_login_response(
                session_token
            )
            await user_manager.on_after_login(user, request, login_response)
            await save_grant(user, session_token, grant, exchange.expires_in)
            for cookie in login_response.headers.getlist("set-cookie"):
                response.headers.append("set-cookie", cookie)
        except Exception:
            await strategy.destroy_token(session_token, user)
            raise
    except Exception:
        try:
            await app_client.revoke(exchange.grant_token)
        except OnyxError:
            pass
        raise

    if existing_token and current is not None:
        await revoke_session_grant(current, existing_token)
        await strategy.destroy_token(existing_token, current)
    response.headers["Cache-Control"] = "no-store"
    return response


async def _bound_user(
    sub2api_user_id: int,
    email: str,
    current: User | None,
    manager: UserManager,
    db_session: Session,
) -> User:
    lock_key = f"onyx:sub2api:{sub2api_user_id}"
    if not db_session.scalar(
        select(func.pg_try_advisory_xact_lock(func.hashtextextended(lock_key, 0)))
    ):
        raise OnyxError(
            OnyxErrorCode.CONFLICT, "Sub2API sign-in is already in progress."
        )
    bindings = db_session.scalars(
        select(Sub2APIUserCredential).where(
            Sub2APIUserCredential.sub2api_user_id == sub2api_user_id
        )
    ).all()
    if len(bindings) > 1 or (
        current is not None and (not bindings or bindings[0].user_id != current.id)
    ):
        raise OnyxError(
            OnyxErrorCode.UNAUTHORIZED, "Sub2API account does not match the session."
        )
    if bindings:
        try:
            user = await manager.get(bindings[0].user_id)
        except exceptions.UserNotExists:
            raise OnyxError(
                OnyxErrorCode.UNAUTHORIZED, "Sub2API account is unavailable."
            ) from None
    else:
        try:
            user = await manager.create(
                UserCreate(
                    email=email.strip().lower(),
                    password=_generate_secure_password(),
                    is_superuser=False,
                    account_type=AccountType.STANDARD,
                    is_verified=True,
                ),
                sub2api_provisioning=True,
            )
        except exceptions.UserAlreadyExists:
            raise OnyxError(
                OnyxErrorCode.CONFLICT,
                "Sub2API account requires an existing verified binding.",
            ) from None
        upsert_sub2api_credential_for_user(
            db_session,
            user,
            Sub2APICredentialPayload(
                api_key_id=0,
                api_key="",
                api_base_url="",
                text_model_name="",
                image_model_name="",
            ),
            sub2api_user_id=sub2api_user_id,
        )
        db_session.commit()
    if not user.is_active or not user.account_type.is_web_login():
        raise OnyxError(OnyxErrorCode.UNAUTHORIZED, "Sub2API account is unavailable.")
    return user


async def require_grant(request: Request, user: User) -> AppGrant:
    grant = await get_grant(user, request.cookies.get(FASTAPI_USERS_AUTH_COOKIE_NAME))
    if grant is None:
        raise OnyxError(OnyxErrorCode.UNAUTHENTICATED, "Sign in again from Sub2API.")
    return grant


@router.get("/session")
async def session(
    request: Request,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> dict[str, int | bool | None]:
    if not SUB2API_LAUNCH_ORIGIN or user.is_anonymous:
        return {"user_id": None, "authorized": False}
    binding = get_sub2api_credential_for_user(db_session, user.id)
    if binding is None or binding.sub2api_user_id <= 0:
        return {"user_id": None, "authorized": False}
    grant = await get_grant(user, request.cookies.get(FASTAPI_USERS_AUTH_COOKIE_NAME))
    return {"user_id": binding.sub2api_user_id, "authorized": grant is not None}


@router.get("/keys")
async def keys(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    user: User = Depends(current_user),
) -> KeyPage:
    grant = await require_grant(request, user)
    return await app_client.list_keys(grant.grant_token, page, page_size)


@router.get("/keys/{key_id}/models")
async def models(
    request: Request,
    key_id: Annotated[int, Path(gt=0)],
    user: User = Depends(current_user),
) -> KeyModels:
    grant = await require_grant(request, user)
    return await app_client.key_models(grant.grant_token, key_id)


@router.post("/revoke")
async def revoke(request: Request, user: User = Depends(current_user)) -> None:
    await revoke_session_grant(
        user, request.cookies.get(FASTAPI_USERS_AUTH_COOKIE_NAME)
    )
