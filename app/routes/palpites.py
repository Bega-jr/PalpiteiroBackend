from fastapi import APIRouter, HTTPException
from app.services import palpites_service

router = APIRouter(prefix="/palpites", tags=["Palpites"])

@router.get("/fixo")
def palpite_fixo():
    registro = palpites_service.obter_palpite_fixo_publico()
    if not registro:
        raise HTTPException(status_code=404, detail="Palpite fixo não encontrado para hoje")

    return {
        "data_referencia": registro.get("data_referencia"),
        "numeros": registro.get("numeros", []),
        "soma": registro.get("soma_total", 0),  # Mapeia soma_total para soma (frontend espera 'soma')
        "pares": registro.get("pares", 0),
        "impares": registro.get("impares", 0),
        "metricas": registro.get("metricas", {}),
    }

@router.get("/estatisticos")
def palpites_estatisticos():
    dados = palpites_service.obter_palpites_estatisticos_publico()

    if not dados:
        return {
            "data_referencia": None,
            "total": 0,
            "palpites": []
        }

    data_referencia = dados[0].get("data_referencia")

    palpites = [
        {
            "indice_palpite": r.get("indice_palpite"),
            "numeros": r.get("numeros", []),
            "soma": r.get("soma_total", 0),  # Mapeia soma_total para soma
            "pares": r.get("pares", 0),
            "score": (r.get("metricas") or {}).get("score", 0),
        }
        for r in dados
    ]

    return {
        "data_referencia": data_referencia,
        "total": len(palpites),
        "palpites": palpites,
    }
