import argparse
import contextlib
import io
import math
import random
import statistics
from unittest.mock import patch

import numpy as np

from app.services import estatisticas_combinacao_v3
from app.services import recompensa_evolutiva_service
from app.services.estatisticas_service import carregar_historico
from app.services.meta_learning_service import PESOS_DEFAULT
from scripts import gerar_palpites_diarios as gerador


MINIMO_HISTORICO_TREINO = 120
REPLICAS_ALEATORIAS_PADRAO = 20


class SupabaseVazio:
    """Isola o backtest das memórias persistidas no Supabase."""

    def table(self, _nome):
        return self

    def select(self, *_args, **_kwargs):
        return self

    def execute(self):
        return type("Response", (), {"data": []})()


def validar_historico(historico):
    if not historico:
        raise ValueError("O histórico oficial está vazio.")

    concursos_vistos = set()
    ultimo_concurso = 0
    for registro in historico:
        concurso = int(registro["concurso"])
        numeros = registro.get("numeros")
        if concurso <= ultimo_concurso or concurso in concursos_vistos:
            raise ValueError("Os concursos devem estar em ordem crescente e sem duplicatas.")
        if (
            not isinstance(numeros, list)
            or len(numeros) != 15
            or any(type(numero) is not int or not 1 <= numero <= 25 for numero in numeros)
            or len(set(numeros)) != 15
        ):
            raise ValueError(f"O concurso {concurso} não contém 15 dezenas válidas.")
        concursos_vistos.add(concurso)
        ultimo_concurso = concurso

    return historico


def validar_portfolio(jogos, quantidade):
    if len(jogos) != quantidade:
        raise RuntimeError(
            f"Gerador retornou {len(jogos)} jogos; eram esperados {quantidade}."
        )

    combinacoes = set()
    for numeros in jogos:
        if (
            not isinstance(numeros, list)
            or len(numeros) != 15
            or any(type(numero) is not int or not 1 <= numero <= 25 for numero in numeros)
            or len(set(numeros)) != 15
        ):
            raise RuntimeError("O gerador retornou um jogo inválido.")
        combinacao = tuple(sorted(numeros))
        if combinacao in combinacoes:
            raise RuntimeError("O gerador retornou jogos duplicados.")
        combinacoes.add(combinacao)


def gerar_portfolio_aleatorio(quantidade, rng, combinacoes_excluidas):
    jogos = []
    combinacoes = set(combinacoes_excluidas)
    while len(jogos) < quantidade:
        jogo = tuple(sorted(rng.sample(range(1, 26), 15)))
        if jogo in combinacoes:
            continue
        combinacoes.add(jogo)
        jogos.append(list(jogo))
    return jogos


def calcular_acertos(jogos, resultado):
    sorteadas = set(resultado)
    return [len(set(jogo) & sorteadas) for jogo in jogos]


def _gerar_portfolio_modelo(historico_treino, concurso_alvo, seed):
    random.seed(seed)
    np.random.seed(seed % (2**32))
    recompensa_evolutiva_service.historico_clusters.clear()

    def scores_somente_treino():
        return estatisticas_combinacao_v3.calcular_score_combinacoes_reais(
            historico=historico_treino
        )

    with (
        patch.object(gerador, "carregar_historico", return_value=historico_treino),
        patch.object(gerador, "get_supabase", return_value=SupabaseVazio()),
        patch.object(
            gerador,
            "calcular_score_combinacoes_reais",
            side_effect=scores_somente_treino,
        ),
        patch.object(
            gerador,
            "obter_fator_aprendizado_global",
            return_value={"fator": 1.0},
        ),
        patch.object(
            gerador,
            "obter_pesos_ensemble",
            return_value=PESOS_DEFAULT.copy(),
        ),
        contextlib.redirect_stdout(io.StringIO()),
    ):
        resultado = gerador.executar_motor_geracao(
            concurso_alvo=concurso_alvo,
            modo_variacao="moderado",
        )

    palpites = resultado.get("palpites", [])
    jogos = [palpite["numeros"] for palpite in palpites]
    validar_portfolio(jogos, gerador.QTD_FINAL)
    return jogos


def executar_backtest(
    historico,
    ultimos=100,
    seed=20261119,
    replicas_aleatorias=REPLICAS_ALEATORIAS_PADRAO,
):
    historico = validar_historico(historico)
    if ultimos < 1:
        raise ValueError("O número de concursos a avaliar deve ser positivo.")
    if replicas_aleatorias < 1:
        raise ValueError("É necessário ao menos um portfólio aleatório por concurso.")

    inicio = len(historico) - ultimos
    if inicio < MINIMO_HISTORICO_TREINO:
        raise ValueError(
            f"São necessários pelo menos {MINIMO_HISTORICO_TREINO} concursos "
            "anteriores para cada previsão."
        )

    quantidade = gerador.QTD_FINAL
    acertos_modelo = []
    acertos_aleatorios = []
    medias_modelo_por_concurso = []
    medias_aleatorias_por_concurso = []
    melhores_modelo = []
    melhores_aleatorio = []

    for indice in range(inicio, len(historico)):
        treino = historico[:indice]
        alvo = historico[indice]
        seed_concurso = seed + int(alvo["concurso"])
        jogos_modelo = _gerar_portfolio_modelo(
            treino,
            int(alvo["concurso"]),
            seed_concurso,
        )
        resultado = alvo["numeros"]
        pontos_modelo = calcular_acertos(jogos_modelo, resultado)
        acertos_modelo.extend(pontos_modelo)
        medias_modelo_por_concurso.append(statistics.mean(pontos_modelo))
        melhores_modelo.append(max(pontos_modelo))

        sorteios_anteriores = {
            tuple(sorted(concurso["numeros"]))
            for concurso in treino
        }
        rng = random.Random(seed_concurso ^ 0x5EED)
        medias_aleatorias = []
        for _ in range(replicas_aleatorias):
            jogos_aleatorios = gerar_portfolio_aleatorio(
                quantidade,
                rng,
                sorteios_anteriores,
            )
            pontos_aleatorios = calcular_acertos(jogos_aleatorios, resultado)
            acertos_aleatorios.extend(pontos_aleatorios)
            medias_aleatorias.append(statistics.mean(pontos_aleatorios))
            melhores_aleatorio.append(max(pontos_aleatorios))
        medias_aleatorias_por_concurso.append(statistics.mean(medias_aleatorias))

    diferencas = [
        modelo - aleatorio
        for modelo, aleatorio in zip(
            medias_modelo_por_concurso,
            medias_aleatorias_por_concurso,
        )
    ]
    delta_medio = statistics.mean(diferencas)
    erro_padrao = (
        statistics.stdev(diferencas) / math.sqrt(len(diferencas))
        if len(diferencas) > 1
        else 0.0
    )

    return {
        "concursos_avaliados": ultimos,
        "primeiro_concurso": int(historico[inicio]["concurso"]),
        "ultimo_concurso": int(historico[-1]["concurso"]),
        "quantidade_jogos": quantidade,
        "replicas_aleatorias": replicas_aleatorias,
        "media_acertos_modelo": statistics.mean(acertos_modelo),
        "media_acertos_aleatorio": statistics.mean(acertos_aleatorios),
        "delta_media_acertos": statistics.mean(acertos_modelo)
        - statistics.mean(acertos_aleatorios),
        "delta_por_concurso": delta_medio,
        "ic95_delta_por_concurso": [
            delta_medio - 1.96 * erro_padrao,
            delta_medio + 1.96 * erro_padrao,
        ],
        "melhor_media_modelo": statistics.mean(melhores_modelo),
        "melhor_media_aleatoria": statistics.mean(melhores_aleatorio),
        "acertos_13_mais_modelo_por_1000": (
            sum(acertos >= 13 for acertos in acertos_modelo)
            / len(acertos_modelo)
            * 1000
        ),
        "acertos_13_mais_aleatorio_por_1000": (
            sum(acertos >= 13 for acertos in acertos_aleatorios)
            / len(acertos_aleatorios)
            * 1000
        ),
        "acertos_14_mais_modelo_por_1000": (
            sum(acertos >= 14 for acertos in acertos_modelo)
            / len(acertos_modelo)
            * 1000
        ),
        "acertos_14_mais_aleatorio_por_1000": (
            sum(acertos >= 14 for acertos in acertos_aleatorios)
            / len(acertos_aleatorios)
            * 1000
        ),
        "acertos_15_modelo": sum(acertos == 15 for acertos in acertos_modelo),
        "acertos_15_aleatorio": sum(acertos == 15 for acertos in acertos_aleatorios),
        "concursos_com_15_modelo": sum(acertos == 15 for acertos in melhores_modelo),
        "concursos_com_15_aleatorio": sum(
            acertos == 15 for acertos in melhores_aleatorio
        ),
    }


def imprimir_relatorio(resultado):
    total_jogos_modelo = (
        resultado["concursos_avaliados"] * resultado["quantidade_jogos"]
    )
    total_jogos_aleatorios = total_jogos_modelo * resultado["replicas_aleatorias"]
    ci_inferior, ci_superior = resultado["ic95_delta_por_concurso"]

    print("BACKTEST WALK-FORWARD")
    print(
        f"Concursos: {resultado['primeiro_concurso']}–{resultado['ultimo_concurso']} "
        f"({resultado['concursos_avaliados']} alvos)"
    )
    print(
        f"Jogos: {resultado['quantidade_jogos']} por portfólio; "
        f"{resultado['replicas_aleatorias']} portfólios aleatórios por alvo"
    )
    print(
        "Memória adaptativa do Supabase neutralizada; scores de cada previsão "
        "recalculados apenas com concursos anteriores."
    )
    print(
        f"Média por jogo: modelo={resultado['media_acertos_modelo']:.4f} | "
        f"aleatório={resultado['media_acertos_aleatorio']:.4f} | "
        f"delta={resultado['delta_media_acertos']:+.4f}"
    )
    print(
        f"Delta médio pareado por concurso: {resultado['delta_por_concurso']:+.4f} "
        f"(IC95% aproximado {ci_inferior:+.4f} a {ci_superior:+.4f})"
    )
    print(
        f"Média do melhor jogo por concurso: "
        f"modelo={resultado['melhor_media_modelo']:.4f} | "
        f"aleatório={resultado['melhor_media_aleatoria']:.4f}"
    )
    print(
        "Acertos por 1.000 jogos (13+ / 14+): "
        f"modelo={resultado['acertos_13_mais_modelo_por_1000']:.2f} / "
        f"{resultado['acertos_14_mais_modelo_por_1000']:.2f}; "
        f"aleatório={resultado['acertos_13_mais_aleatorio_por_1000']:.2f} / "
        f"{resultado['acertos_14_mais_aleatorio_por_1000']:.2f}"
    )
    print(
        f"15 acertos: modelo={resultado['acertos_15_modelo']}/{total_jogos_modelo}; "
        f"aleatório={resultado['acertos_15_aleatorio']}/{total_jogos_aleatorios} "
        f"(portfólios com jackpot: "
        f"{resultado['concursos_com_15_modelo']} vs "
        f"{resultado['concursos_com_15_aleatorio']})"
    )
    print(
        "Referência teórica: 9 acertos esperados por jogo aleatório; "
        f"15/15 em um jogo = 1 em {math.comb(25, 15):,}."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Compara o gerador com jogos aleatórios em validação cronológica."
    )
    parser.add_argument(
        "--ultimos",
        type=int,
        default=100,
        help="Quantidade de concursos finais a avaliar (padrão: 100).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261119,
        help="Semente para reproduzir a geração (padrão: 20261119).",
    )
    parser.add_argument(
        "--replicas-aleatorias",
        type=int,
        default=REPLICAS_ALEATORIAS_PADRAO,
        help="Portfólios aleatórios por concurso (padrão: 20).",
    )
    args = parser.parse_args()

    historico = carregar_historico()
    resultado = executar_backtest(
        historico,
        ultimos=args.ultimos,
        seed=args.seed,
        replicas_aleatorias=args.replicas_aleatorias,
    )
    imprimir_relatorio(resultado)


if __name__ == "__main__":
    main()
