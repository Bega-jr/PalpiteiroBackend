from fastapi import APIRouter, HTTPException
from app.services.palpites_service import (
    obter_palpite_fixo_publico,
    obter_palpites_estatisticos_publico
)

router = APIRouter(prefix="/palpites", tags=["Palpites"])


@router.get("/fixo")
def palpite_fixo():
    registro = obter_palpite_fixo_publico()

    if not registro:
        raise HTTPException(status_code=404, detail="Palpite fixo não encontrado")

    return {
        "status": "ok",
        "data_referencia": registro.get("data_referencia"),
        "numeros": registro.get("numeros"),
        "soma": registro.get("soma_total"),
        "pares": registro.get("pares"),
        "impares": registro.get("impares"),
        "score": registro.get("metricas", {}).get("score"),
        "metodo": registro.get("metricas", {}).get("metodo"),
    }


@router.get("/estatisticos")
def palpites_estatisticos():
    dados = obter_palpites_estatisticos_publico()

    palpites = [
        {
            "indice": r.get("indice_palpite"),
            "numeros": r.get("numeros"),
            "soma": r.get("soma"),
            "pares": r.get("pares"),
            "impares": r.get("impares"),
            "score": r.get("metricas", {}).get("score"),
            "metodo": r.get("metricas", {}).get("metodo"),
        }
        for r in dados
    ]

    return {
        "status": "ok",
        "data_referencia": dados[0].get("data_referencia") if dados else None,
        "total": len(palpites),
        "palpites": palpites,
    }

