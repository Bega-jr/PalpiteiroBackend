from fastapi import APIRouter, HTTPException
from app.services import palpites_service
from datetime import date

router = APIRouter(prefix="/palpites", tags=["Palpites"])

@router.get("/fixo")
def palpite_fixo():
    try:
        registro = palpites_service.obter_palpite_fixo_publico()
        if not registro:
            raise HTTPException(status_code=404, detail="Palpite não encontrado")

        # Montamos a resposta usando as colunas reais da sua tabela
        return {
            "status": "ok",
            "data_referencia": registro.get("data_referencia"),
            "numeros": registro.get("numeros"),
            "soma": registro.get("soma_total"),
            "pares": registro.get("pares"),
            "impares": registro.get("impares"),
            "metricas": registro.get("metricas")
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/estatisticos")
def palpites_estatisticos():
    try:
        dados_brutos = palpites_service.obter_palpites_estatisticos_publico()
        
        # Formatamos a lista para o Front
        palpites_formatados = []
        for r in dados_brutos:
            palpites_formatados.append({
                "indice": r.get("indice_palpite"),
                "numeros": r.get("numeros"),
                "soma": r.get("soma_total"),
                "pares": r.get("pares"),
                "score": r.get("metricas", {}).get("score", 0) if r.get("metricas") else 0
            })

        return {
            "status": "ok",
            "total": len(palpites_formatados),
            "palpites": palpites_formatados
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

