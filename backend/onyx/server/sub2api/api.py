import secrets
import string
import uuid

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi_users import exceptions
from fastapi_users.authentication import Strategy
from sqlalchemy.orm import Session

from onyx.auth.schemas import UserCreate
from onyx.auth.schemas import UserRole
from onyx.auth.users import auth_backend
from onyx.auth.users import get_user_manager
from onyx.auth.users import UserManager
from onyx.configs.app_configs import SUB2API_INTEGRATION_ENABLED
from onyx.configs.app_configs import SUB2API_ONYX_REDIRECT_PATH
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import AccountType
from onyx.db.models import User
from onyx.db.sub2api_user_credentials import upsert_sub2api_credential_for_user
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.server.sub2api.client import exchange_sub2api_launch_token

router = APIRouter(prefix="/sub2api")


@router.get("/exchange")
async def sub2api_exchange(
    request: Request,
    token: str,
    strategy: Strategy[User, uuid.UUID] = Depends(auth_backend.get_strategy),
    user_manager: UserManager = Depends(get_user_manager),
    db_session: Session = Depends(get_session),
) -> RedirectResponse:
    if not SUB2API_INTEGRATION_ENABLED:
        raise OnyxError(
            OnyxErrorCode.SERVICE_UNAVAILABLE,
            "Sub2API integration is disabled.",
        )

    launch_token = token.strip()
    if not launch_token:
        raise OnyxError(
            OnyxErrorCode.MISSING_REQUIRED_FIELD,
            "Missing launch token.",
        )

    exchange = await exchange_sub2api_launch_token(launch_token)
    user = await upsert_onyx_user_from_sub2api(
        email=exchange.user.email,
        username=exchange.user.username,
        user_manager=user_manager,
    )

    if not user.is_active:
        raise OnyxError(OnyxErrorCode.UNAUTHENTICATED, "User is inactive.")
    if not user.account_type.is_web_login():
        raise OnyxError(
            OnyxErrorCode.UNAUTHORIZED,
            "User account does not support web login.",
        )

    upsert_sub2api_credential_for_user(
        db_session,
        user,
        exchange.credential,
        sub2api_user_id=exchange.user.id,
    )
    db_session.commit()

    login_response = await auth_backend.login(strategy, user)
    await user_manager.on_after_login(user, request, login_response)

    redirect_response = RedirectResponse(SUB2API_ONYX_REDIRECT_PATH, status_code=302)
    _copy_login_headers(login_response, redirect_response)
    return redirect_response


async def upsert_onyx_user_from_sub2api(
    *,
    email: str,
    username: str,
    user_manager: UserManager,
) -> User:
    del username
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Sub2API user email is missing.")

    try:
        user = await user_manager.get_by_email(normalized_email)
        if not user.account_type.is_web_login():
            raise OnyxError(
                OnyxErrorCode.UNAUTHORIZED,
                "Existing Onyx user does not support web login.",
            )
        return user
    except exceptions.UserNotExists:
        pass

    return await user_manager.create(
        UserCreate(
            email=normalized_email,
            password=_generate_secure_password(),
            role=UserRole.BASIC,
            account_type=AccountType.STANDARD,
            is_verified=True,
        )
    )


def _generate_secure_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    return "".join(
        [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%^&*()-_=+[]{}|;:,.<>?"),
            "".join(secrets.choice(alphabet) for _ in range(24)),
        ]
    )


def _copy_login_headers(
    login_response: object,
    redirect_response: RedirectResponse,
) -> None:
    for header_name, header_value in login_response.headers.items():
        header_name_lower = header_name.lower()
        if header_name_lower == "set-cookie":
            redirect_response.headers.append(header_name, header_value)
            continue
        if header_name_lower in {"location", "content-length"}:
            continue
        redirect_response.headers[header_name] = header_value
