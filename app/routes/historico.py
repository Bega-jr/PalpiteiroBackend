from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from typing import List
from app.schemas.historico_schema import HistoricoCreate, HistoricoRead
from app.services.historico_service import registrar_jogo, listar_historico, resumo_financeiro
from app.core.auth import get_user

router = APIRouter(prefix="/historico", tags=["Histórico"])


def _authenticated_user_id(user) -> UUID:
    try:
        return UUID(str(user.id))
    except (AttributeError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Usuário autenticado inválido") from exc


# ==========================================
# ADICIONAR JOGO
# ==========================================
@router.post("/", response_model=HistoricoRead)
def criar_jogo(
    jogo: HistoricoCreate,
    user=Depends(get_user),
):
    return registrar_jogo(_authenticated_user_id(user), jogo)

# ==========================================
# LISTAR HISTÓRICO
# ==========================================
@router.get("/", response_model=List[HistoricoRead])
def obter_historico(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user=Depends(get_user),
):
    return listar_historico(_authenticated_user_id(user), page=page, limit=limit)

# ==========================================
# RESUMO FINANCEIRO
# ==========================================
@router.get("/resumo")
def obter_resumo(user=Depends(get_user)):
    return resumo_financeiro(_authenticated_user_id(user))
