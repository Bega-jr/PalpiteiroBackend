from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import List
from app.schemas.historico_schema import HistoricoCreate, HistoricoRead
from app.services.historico_service import registrar_jogo, listar_historico, resumo_financeiro
from app.dependencies.auth import get_user  # Função que retorna o usuário logado

router = APIRouter(prefix="/historico", tags=["Histórico"])

# ==========================================
# ADICIONAR JOGO
# ==========================================
@router.post("/", response_model=HistoricoRead)
def criar_jogo(jogo: HistoricoCreate, user=Depends(get_user)):
    """
    Registra um novo jogo para o usuário autenticado.
    """
    try:
        return registrar_jogo(user.id, jogo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==========================================
# LISTAR HISTÓRICO
# ==========================================
@router.get("/", response_model=List[HistoricoRead])
def obter_historico(user=Depends(get_user)):
    """
    Retorna todos os jogos do usuário logado.
    """
    return listar_historico(user.id)

# ==========================================
# RESUMO FINANCEIRO
# ==========================================
@router.get("/resumo")
def obter_resumo(user=Depends(get_user)):
    """
    Calcula estatísticas financeiras do usuário logado.
    """
    return resumo_financeiro(user.id)

