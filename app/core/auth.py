from fastapi import Depends, HTTPException, Header
from datetime import datetime, timezone, timedelta
from typing import Dict
from threading import Lock, Thread
import time
from app.core.supabase import supabase
import logging

# Configura logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth_cache")

# Cache de tokens
token_cache: Dict[str, dict] = {}
cache_lock = Lock()

# Intervalo para limpeza automática (em segundos)
CLEANUP_INTERVAL = 60  # limpa a cada minuto

def cleanup_cache():
    """
    Remove tokens expirados do cache periodicamente.
    Deve rodar em uma thread separada.
    """
    while True:
        time.sleep(CLEANUP_INTERVAL)
        now_ts = datetime.now(timezone.utc).timestamp()
        with cache_lock:
            expired_tokens = [t for t, v in token_cache.items() if v["expires_at"] < now_ts]
            for t in expired_tokens:
                del token_cache[t]
                logger.debug(f"Token removido do cache: {t}")

# Inicia a thread de limpeza em background
cleanup_thread = Thread(target=cleanup_cache, daemon=True)
cleanup_thread.start()

def validate_token(token: str):
    """
    Valida token com Supabase, usando cache em memória.
    """
    now_ts = datetime.now(timezone.utc).timestamp()

    # Checa cache
    with cache_lock:
        cached = token_cache.get(token)
        if cached:
            if cached["expires_at"] < now_ts:
                del token_cache[token]
                logger.info("Token expirado no cache")
            else:
                return cached["user"]

    # Consulta Supabase
    user_response = supabase.auth.get_user(token)
    if not user_response or not getattr(user_response, "user", None):
        logger.warning(f"Tentativa de acesso com token inválido: {token}")
        raise HTTPException(status_code=401, detail="Não autorizado")

    user = user_response.user

    # Expiração do token
    token_exp = getattr(user, "token_exp", None)
    if token_exp and now_ts > token_exp:
        logger.info(f"Token expirado: {token}")
        raise HTTPException(status_code=401, detail="Token expirado")

    # Salva no cache
    with cache_lock:
        token_cache[token] = {
            "user": user,
            "expires_at": token_exp if token_exp else now_ts + 300  # 5 min default
        }

    return user

def get_user(authorization: str = Header(...)):
    """
    Recupera usuário autenticado do header Authorization.
    """
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("Authorization header inválido ou ausente")
        raise HTTPException(status_code=401, detail="Não autorizado")

    token = authorization.split(" ")[1]
    return validate_token(token)
