from fastapi import APIRouter
from app.services import palpites_service

router = APIRouter(prefix="/palpites", tags=["Palpites"])

@router.get("/fixo")
@router.get("/estatisticos")
def testar_tudo():
    # Retorna o dicionário completo do service para vermos o erro
    resultado = palpites_service.obter_palpites_estatisticos_publico()
    return resultado
