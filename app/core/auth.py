from fastapi import HTTPException, Header
import logging
import time
from threading import Lock

from app.services.supabase_service import get_supabase

logger = logging.getLogger("auth_cache")

token_cache: dict[str, dict] = {}
cache_lock = Lock()
MAX_TOKEN_CACHE_ENTRIES = 1024


def validate_token(token: str):
    now_ts = time.time()

    with cache_lock:
        expired = [
            cached_token
            for cached_token, value in token_cache.items()
            if value["expires_at"] <= now_ts
        ]
        for cached_token in expired:
            del token_cache[cached_token]

        cached = token_cache.get(token)
        if cached and cached["expires_at"] > now_ts:
            return cached["user"]

    try:
        response = get_supabase().auth.get_user(token)
    except Exception as exc:
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        try:
            status = int(status)
        except (TypeError, ValueError):
            status = None
        if status in (400, 401, 403):
            raise HTTPException(status_code=401, detail="Token inválido") from exc

        logger.exception("Falha ao validar token de autenticação")
        raise HTTPException(
            status_code=503,
            detail="Serviço de autenticação indisponível",
        ) from exc

    user = getattr(response, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Não autorizado")

    expires_at = getattr(user, "token_exp", None)
    if not isinstance(expires_at, (int, float)) or expires_at <= now_ts:
        expires_at = now_ts + 300

    with cache_lock:
        if len(token_cache) >= MAX_TOKEN_CACHE_ENTRIES:
            token_cache.pop(next(iter(token_cache)))
        token_cache[token] = {
            "user": user,
            "expires_at": expires_at
        }

    return user


def get_user(authorization: str = Header(...)):
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Token ausente")

    return validate_token(token.strip())

