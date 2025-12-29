from fastapi import Depends, HTTPException, Header
from app.core.supabase import supabase


def get_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token inválido")

    token = authorization.replace("Bearer ", "")

    user = supabase.auth.get_user(token)

    if not user:
        raise HTTPException(401, "Usuário não autenticado")

    return user.user
