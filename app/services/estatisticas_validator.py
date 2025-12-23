from app.services.estatisticas_services import calcular_metricas_jogo

REGRAS_PADRAO = {
    "soma": (170, 210),
    "pares": (6, 9),
    "sequencia_max": 5
}


def validar_jogo(jogo, regras=REGRAS_PADRAO):
    metricas = calcular_metricas_jogo(jogo)

    return {
        "aprovado": (
            regras["soma"][0] <= metricas["soma"] <= regras["soma"][1]
            and regras["pares"][0] <= metricas["pares"] <= regras["pares"][1]
            and metricas["maior_sequencia"] <= regras["sequencia_max"]
        ),
        "metricas": metricas
    }


def filtrar_jogos_validos(lista_jogos):
    return [
        jogo for jogo in lista_jogos
        if validar_jogo(jogo)["aprovado"]
    ]

