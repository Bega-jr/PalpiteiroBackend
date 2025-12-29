from fastapi import APIRouter, Depends, HTTPException
from app.core.supabase import obter_usuario_logado # Usando a função de validação que criamos
from app.services.historico_service import (
    salvar_jogo,
    listar_historico,
    resumo_financeiro
)

router = APIRouter(prefix="/historico", tags=["Histórico"])

# ==========================================
# REGISTRAR JOGO (ROTA PROTEGIDA)
# ==========================================
@router.post("/")
def registrar(jogo: dict, user_id: str = Depends(obter_usuario_logado)):
    """
    Salva um palpite para o usuário logado.
    """
    try:
        # Chamamos o serviço passando o user_id extraído do Token JWT
        salvar_jogo(
            user_id=user_id,
            tipo=jogo.get("tipo", "estatistico"),
            numeros=jogo.get("numeros"),
            score=jogo.get("score")
        )
        return {"status": "ok", "message": "Jogo salvo com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==========================================
# LISTAR HISTÓRICO (ROTA PROTEGIDA)
# ==========================================
@router.get("/")
def listar(user_id: str = Depends(obter_usuario_logado)):
    """
    Retorna a lista de jogos salvos apenas do usuário logado.
    """
    return listar_historico(user_id)

# ==========================================
# RESUMO DE ROI/FINANCEIRO (ROTA PROTEGIDA)
# ==========================================
@router.get("/resumo")
def resumo(user_id: str = Depends(obter_usuario_logado)):
    """
    Calcula o ROI e estatísticas financeiras do usuário logado.
    """
    return resumo_financeiro(user_id)
