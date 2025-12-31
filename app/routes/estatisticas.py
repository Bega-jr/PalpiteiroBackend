from fastapi import APIRouter, HTTPException
from app.repositories.estatisticas_repo import (
    carregar_estatisticas_base,
    carregar_estatisticas_score
)

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

@router.get("/base")
def estatisticas_base():
    try:
        # Se o repo.py estiver ajustado, ele retornará uma lista vazia ou dados antigos
        # e nunca lançará uma exceção aqui.
        dados = carregar_estatisticas_base()
        return {
            "status": "ok",
            "dados": dados
        }
    except Exception as e:
        # Caso o Supabase esteja TOTALMENTE inacessível ou outro erro grave ocorra,
        # o erro 500 será retornado com uma mensagem mais genérica e segura.
        print(f"ERRO CRÍTICO no endpoint /base: {e}")
        raise HTTPException(status_code=500, detail="Erro interno no servidor ao carregar estatísticas.")


@router.get("/score")
def estatisticas_score():
    try:
        # Se o repo.py estiver ajustado, ele retornará uma lista vazia ou dados antigos
        # e nunca lançará uma exceção aqui.
        dados = carregar_estatisticas_score()
        return {
            "status": "ok",
            "dados": dados
        }
    except Exception as e:
        # Caso o Supabase esteja TOTALMENTE inacessível ou outro erro grave ocorra,
        # o erro 500 será retornado com uma mensagem mais genérica e segura.
        print(f"ERRO CRÍTICO no endpoint /score: {e}")
        raise HTTPException(status_code=500, detail="Erro interno no servidor ao carregar scores.")
