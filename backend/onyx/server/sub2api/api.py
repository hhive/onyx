import contextlib
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import status
from fastapi.responses import RedirectResponse
from fastapi_users import exceptions
from fastapi_users.authentication import Strategy

from onyx.auth.schemas import UserCreate
from onyx.auth.users import auth_backend
from onyx.auth.users import generate_password
from onyx.auth.users import get_user_manager
from onyx.auth.users import UserManager
from onyx.configs.app_configs import SUB2API_INTEGRATION_ENABLED
from onyx.configs.app_configs import SUB2API_ONYX_REDIRECT_PATH
from onyx.configs.constants import PUBLIC_API_TAGS
from onyx.db.auth import get_user_db
from onyx.db.engine.async_sql_engine import get_async_session_context_manager
from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.db.models import User
from onyx.db.sub2api_user_credentials import upsert_sub2api_user_credentials
from onyx.server.sub2api.client import Sub2APIClient
from onyx.server.sub2api.service import map_sub2api_role_to_onyx_role
from onyx.server.sub2api.service import update_user_role_from_sub2api

router = APIRouter(prefix="/auth/sub2api")
legacy_router = APIRouter(prefix="/sub2api")


def _sanitize_redirect_path(candidate: str | None) -> str:
    if not candidate:
        return SUB2API_ONYX_REDIRECT_PATH

    redirect_path = candidate.strip()
    if not redirect_path.startswith("/") or "\\" in redirect_path:
        return SUB2API_ONYX_REDIRECT_PATH

    parsed = urlparse(redirect_path)
    if parsed.scheme or parsed.netloc:
        return SUB2API_ONYX_REDIRECT_PATH

    return redirect_path


async def _upsert_sub2api_user(email: str, role: str, request: Request) -> User:
    get_user_db_context = contextlib.asynccontextmanager(get_user_db)
    get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)

    async with get_async_session_context_manager() as session:
        async with get_user_db_context(session) as user_db:
            async with get_user_manager_context(user_db) as user_manager:
                try:
                    user = await user_manager.get_by_email(email)
                    if not user.account_type.is_web_login():
                        raise exceptions.UserNotExists()
                except exceptions.UserNotExists:
                    user = await user_manager.create(
                        UserCreate(
                            email=email,
                            password=generate_password(),
                            role=map_sub2api_role_to_onyx_role(role),
                            is_verified=True,
                        ),
                        request=request,
                    )

                if update_user_role_from_sub2api(user, role):
                    await user_db.update(user, {"role": user.role})

                return user


def _copy_auth_headers(auth_response: Response, redirect_response: Response) -> None:
    for header_name, header_value in auth_response.headers.items():
        header_name_lower = header_name.lower()
        if header_name_lower == "set-cookie":
            redirect_response.headers.append(header_name, header_value)
            continue
        if header_name_lower in {"location", "content-length"}:
            continue
        redirect_response.headers[header_name] = header_value


@router.get("/callback", tags=PUBLIC_API_TAGS)
async def sub2api_login_callback(
    request: Request,
    token: str,
    next: str | None = None,  # noqa: A002 - query parameter name matches login flows
    strategy: Strategy[User, UUID] = Depends(auth_backend.get_strategy),
    user_manager: UserManager = Depends(get_user_manager),
) -> Response:
    if not SUB2API_INTEGRATION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub2API integration is disabled.",
        )

    payload = Sub2APIClient().exchange_launch_token(token)
    user = await _upsert_sub2api_user(payload.email, payload.role, request)

    with get_session_with_current_tenant() as db_session:
        upsert_sub2api_user_credentials(
            db_session,
            user_id=user.id,
            sub2api_user_id=payload.user_id,
            api_key=payload.api_key,
        )
        db_session.commit()

    auth_response = await auth_backend.login(strategy, user)
    await user_manager.on_after_login(user, request, auth_response)

    redirect_response = RedirectResponse(_sanitize_redirect_path(next), status_code=302)
    _copy_auth_headers(auth_response, redirect_response)
    return redirect_response


legacy_router.add_api_route(
    "/exchange",
    sub2api_login_callback,
    methods=["GET"],
    tags=PUBLIC_API_TAGS,
)
