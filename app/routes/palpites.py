from fastapi import APIRouter, HTTPException, Depends
from app.services.palpites_service import gerar_palpite_fixo, gerar_7_palpites

router = APIRouter(prefix="/palpites", tags=["Palpites"])

@router.get("/fixo")
def palpite_fixo():
    # Rota pública: qualquer um vê, mas ninguém salva no banco aqui
    try:
        numeros = gerar_palpite_fixo()
        return {"status": "ok", "tipo": "fixo", "numeros": numeros}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/estatisticos")
def palpites_estatisticos():
    # Rota pública: gera os 7 palpites para o cliente escolher
    try:
        palpites = gerar_7_palpites()
        return {"status": "ok", "tipo": "estatistico", "palpites": palpites}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
