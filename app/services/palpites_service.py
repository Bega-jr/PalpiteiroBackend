from datetime import date
from app.repositories.palpites_repo import (
    listar_palpites_hoje,
    carregar_palpite_fixo
)

# =====================================================
# SERVIÇO DE PALPITES (APENAS LEITURA)
# Fonte da verdade: Supabase
# =====================================================


def obter_palpite_fixo_publico():
    """
    Retorna o palpite fixo do dia já pré-calculado.
    """
    numeros = carregar_palpite_fixo()

    if not numeros:
        return {
            "status": "indisponivel",
            "mensagem": "Palpite fixo ainda não calculado para hoje"
        }

    return {
        "status": "ok",
        "data_referencia": date.today().isoformat(),
        "numeros": numeros
    }


def obter_palpites_estatisticos_publico():
    """
    Retorna os palpites estatísticos do dia já calculados.
    """
    registros = listar_palpites_hoje()

    if not registros:
        return {
            "status": "indisponivel",
            "mensagem": "Palpites ainda não calculados para hoje"
        }

    palpites = []
    for r in registros:
        palpites.append({
            "indice": r.get("indice_palpite"),
            "numeros": r.get("numeros"),
            "tipo": r.get("tipo"),
            "score": r.get("metricas", {}).get("score"),
        })

    return {
        "status": "ok",
        "data_referencia": date.today().isoformat(),
        "total": len(palpites),
        "palpites": palpites
    }
