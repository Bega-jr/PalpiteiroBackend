from fastapi import APIRouter, HTTPException
from app.services.palpites_service import (
    obter_palpite_fixo_publico,
    obter_palpites_estatisticos_publico,
)

router = APIRouter(prefix="/palpites", tags=["Palpites"])


@router.get("/fixo")
def palpite_fixo():
    registro = obter_palpite_fixo_publico()

    if not registro:
        raise HTTPException(status_code=404, detail="Palpite fixo não encontrado")

    return {
        "status": "ok",
        "data_referencia": registro["data_referencia"],
        "numeros": registro["numeros"],
        "soma": registro["soma"],
        "pares": registro["pares"],
        "impares": registro["impares"],
        "score": registro["metricas"].get("score"),
        "metodo": registro["metricas"].get("metodo"),
    }


@router.get("/estatisticos")
def palpites_estatisticos():
    dados = obter_palpites_estatisticos_publico()

    return {
        "status": "ok",
        "data_referencia": dados[0]["data_referencia"] if dados else None,
        "total": len(dados),
        "palpites": [
            {
                "indice": r["indice_palpite"],
                "numeros": r["numeros"],
                "soma": r["soma"],
                "pares": r["pares"],
                "impares": r["impares"],
                "score": r["metricas"].get("score"),
                "metodo": r["metricas"].get("metodo"),
            }
            for r in dados
        ],
    }
