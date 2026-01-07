from fastapi import APIRouter, HTTPException
from app.services import palpites_service

router = APIRouter(prefix="/palpites", tags=["Palpites"])


@router.get("/fixo")
def palpite_fixo():
    registro = palpites_service.obter_palpite_fixo_publico()

    if not registro:
        raise HTTPException(status_code=404, detail="Palpite fixo não encontrado")

    return {
        "status": "ok",
        "data_referencia": registro.get("data_referencia"),
        "numeros": registro.get("numeros"),
        "soma": registro.get("soma_total"),
        "pares": registro.get("pares"),
        "impares": registro.get("impares"),
        "metricas": registro.get("metricas"),
    }


@router.get("/estatisticos")
def palpites_estatisticos():
    dados = palpites_service.obter_palpites_estatisticos_publico()

    palpites = [
        {
            "indice": r.get("indice_palpite"),
            "numeros": r.get("numeros"),
            "soma": r.get("soma_total"),
            "pares": r.get("pares"),
            "score": (r.get("metricas") or {}).get("score", 0),
        }
        for r in dados
    ]

    return {
        "status": "ok",
        "data_referencia": dados[0]["data_referencia"] if dados else None,
        "total": len(palpites),
        "palpites": palpites,
    }
