from fastapi import HTTPException, Header
from datetime import datetime, timezone
from typing import Dict
from threading import Lock, Thread
import time
import logging

from app.services.supabase_service import get_supabase

supabase = get_supabase()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth_cache")

token_cache: Dict[str, dict] = {}
cache_lock = Lock()

CLEANUP_INTERVAL = 60


def cleanup_cache():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        now_ts = datetime.now(timezone.utc).timestamp()
        with cache_lock:
            expired = [
                t for t, v in token_cache.items()
                if v["expires_at"] < now_ts
            ]
            for t in expired:
                del token_cache[t]


Thread(target=cleanup_cache, daemon=True).start()


def validate_token(token: str):
    now_ts = datetime.now(timezone.utc).timestamp()

    with cache_lock:
        cached = token_cache.get(token)
        if cached and cached["expires_at"] > now_ts:
            return cached["user"]

    try:
        response = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = getattr(response, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Não autorizado")

    expires_at = getattr(user, "token_exp", now_ts + 300)

    with cache_lock:
        token_cache[token] = {
            "user": user,
            "expires_at": expires_at
        }

    return user


def get_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente")

    token = authorization.replace("Bearer ", "")
    return validate_token(token)

