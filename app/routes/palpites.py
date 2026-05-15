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

    # Mapeado como array dentro de 'palpites' para manter o contrato unificado do front-end
    return {
        "status": "ok",
        "data_referencia": registro["data_referencia"],
        "palpites": [
            {
                "numeros": registro["numeros"],
                "soma": registro["soma"],
                "pares": registro["pares"],
                "impares": registro["impares"],
                "score": registro["metricas"].get("score") if registro.get("metricas") else 0,
                "metodo": registro["metricas"].get("metodo") if registro.get("metricas") else "fixo",
            }
        ],
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
                "indice": r.get("indice_palpite", 0),
                "numeros": r.get("numeros", []),
                "soma": r.get("soma", 0),
                "pares": r.get("pares", 0),
                "impares": r.get("impares", 0),
                # Tratamento preventivo com get() seguro para evitar novas falhas 500
                "score": r["metricas"].get("score", 0) if r.get("metricas") else 0,
                "metodo": r["metricas"].get("metodo", "estatistico") if r.get("metricas") else "estatistico",
            }
            for r in dados
        ],
    }
