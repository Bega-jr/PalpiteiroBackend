from fastapi import APIRouter, HTTPException, Header
from uuid import UUID
from typing import List, Optional
from app.schemas.historico_schema import HistoricoCreate, HistoricoRead
from app.services.historico_service import registrar_jogo, listar_historico, resumo_financeiro

router = APIRouter(prefix="/historico", tags=["Histórico"])

# ==========================================
# ADICIONAR JOGO
# ==========================================
@router.post("/", response_model=HistoricoRead)
def criar_jogo(
    jogo: HistoricoCreate, 
    x_user_id: str = Header(..., alias="X-User-Id")
):
    """
    Registra um novo jogo. O user_id é lido do Header 'X-User-Id'.
    """
    try:
        user_uuid = UUID(x_user_id)
        return registrar_jogo(user_uuid, jogo)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==========================================
# LISTAR HISTÓRICO
# ==========================================
@router.get("/", response_model=List[HistoricoRead])
def obter_historico(x_user_id: str = Header(..., alias="X-User-Id")):
    """
    Retorna todos os jogos do usuário.
    """
    try:
        user_uuid = UUID(x_user_id)
        return listar_historico(user_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")

# ==========================================
# RESUMO FINANCEIRO
# ==========================================
@router.get("/resumo")
def obter_resumo(x_user_id: str = Header(..., alias="X-User-Id")):
    """
    Calcula estatísticas financeiras do usuário.
    """
    try:
        user_uuid = UUID(x_user_id)
        return resumo_financeiro(user_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")
