import hashlib

from pydantic import SecretStr

from onyx.configs.app_configs import AUTH_BACKEND, SUB2API_APP_ID
from onyx.configs.constants import AuthBackend
from onyx.db.models import User
from onyx.redis.redis_pool import get_async_redis_connection
from onyx.server.sub2api import app_client
from onyx.server.sub2api.models import AppGrant
from onyx.utils.encryption import decrypt_bytes_to_string, encrypt_string_to_bytes
from onyx.utils.logger import setup_logger

logger = setup_logger()


def _grant_key(user: User, session_token: str) -> str:
    session_id = session_token
    if AUTH_BACKEND == AuthBackend.JWT:
        from onyx.auth.users import get_jwt_strategy

        session_id = (
            get_jwt_strategy().get_session_id(session_token, user) or session_token
        )
    fingerprint = hashlib.sha256(session_id.encode()).hexdigest()
    return f"sub2api:app-grant:{SUB2API_APP_ID}:{user.id}:{fingerprint}"


def _pack_grant(grant: AppGrant) -> bytes:
    user_id = grant.user_id
    return encrypt_string_to_bytes(f"{user_id}:{grant.grant_token.get_secret_value()}")


def _unpack_grant(encrypted: bytes) -> AppGrant:
    user_id, token = decrypt_bytes_to_string(encrypted).split(":", 1)
    return AppGrant(user_id=int(user_id), grant_token=SecretStr(token))


async def save_grant(user: User, session_token: str, grant: AppGrant, ttl: int) -> None:
    # no-direct-redis: allow session store for app grants
    redis = await get_async_redis_connection()
    await redis.set(_grant_key(user, session_token), _pack_grant(grant), ex=ttl)


async def get_grant(user: User, session_token: str | None) -> AppGrant | None:
    if not session_token:
        return None
    # no-direct-redis: allow session store for app grants
    redis = await get_async_redis_connection()
    payload = await redis.get(_grant_key(user, session_token))
    return _unpack_grant(payload) if payload is not None else None


async def revoke_session_grant(user: User, session_token: str | None) -> None:
    if not session_token:
        return
    try:
        # no-direct-redis: allow session store for app grants
        redis = await get_async_redis_connection()
        payload = await redis.getdel(_grant_key(user, session_token))
        if payload is not None:
            await app_client.revoke(_unpack_grant(payload).grant_token)
    except Exception:
        logger.warning("Sub2API session grant revocation failed")
