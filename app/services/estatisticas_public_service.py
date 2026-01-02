from app.repositories.estatisticas_repo import carregar_estatisticas_hoje


def obter_estatisticas_publicas():
    """
    Retorna estatísticas prontas para exibição pública.
    Não executa cálculos pesados.
    """
    dados = carregar_estatisticas_hoje()

    if not dados:
        return {
            "status": "indisponivel",
            "mensagem": "Estatísticas ainda não calculadas para hoje"
        }

    return {
        "status": "ok",
        "data_referencia": dados.get("data_referencia"),
        "numeros_quentes": dados.get("numeros_quentes", []),
        "numeros_frios": dados.get("numeros_frios", []),
        "numeros_atrasados": dados.get("numeros_atrasados", []),
        "media_soma": dados.get("media_soma"),
        "media_pares": dados.get("media_pares"),
        "sequencias_comuns": dados.get("sequencias_comuns", []),
        "faixa_pares": dados.get("faixa_pares"),
    }
