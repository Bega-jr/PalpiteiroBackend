from app.repositories.estatisticas_repo import (
    carregar_estatisticas_base,
    carregar_estatisticas_score,
    carregar_estatisticas_diarias
)


def montar_dashboard_estatisticas():
    base = carregar_estatisticas_base()
    score = carregar_estatisticas_score()
    diario = carregar_estatisticas_diarias()

    if not base or not score:
        return {
            "status": "vazio",
            "mensagem": "Estatísticas ainda não disponíveis"
        }

    scores_validos = [n["score"] for n in score if n.get("score") is not None]

    dashboard = {
        "data": diario["data_referencia"] if diario else None,
        "resumo": {
            "total_numeros": len(base),
            "score_medio": round(sum(scores_validos) / len(scores_validos), 4)
            if scores_validos else None
        },
        "destaques": {
            "mais_quente": score[0]["numero"],
            "mais_atrasado": max(base, key=lambda x: x["atraso"])["numero"]
        },
        "insights": []
    }

    if scores_validos and max(scores_validos) > 0.75:
        dashboard["insights"].append("Existem números com score muito elevado hoje")

    if dashboard["destaques"]["mais_atrasado"]:
        dashboard["insights"].append(
            f"Número {dashboard['destaques']['mais_atrasado']} está muito atrasado"
        )

    return dashboard
