import unittest
from itertools import combinations
from unittest.mock import patch

from scripts import backtest_walk_forward


def criar_historico(qtd):
    historico = []
    for concurso in range(1, qtd + 1):
        numeros = sorted({((concurso + offset - 1) % 25) + 1 for offset in range(15)})
        historico.append({"concurso": concurso, "numeros": numeros})
    return historico


def criar_portfolio_com_acertos(resultado, qtd_acertos):
    fora_do_resultado = sorted(set(range(1, 26)) - set(resultado))
    return [
        sorted((*acertos, *fora))
        for acertos in combinations(resultado, qtd_acertos)
        for fora in combinations(fora_do_resultado, 15 - qtd_acertos)
    ][:20]


class WalkForwardBacktestTests(unittest.TestCase):
    def test_validation_requires_chronological_unique_draws(self):
        historico = criar_historico(2)
        with self.assertRaises(ValueError):
            backtest_walk_forward.validar_historico(historico[::-1])

        with self.assertRaises(ValueError):
            backtest_walk_forward.validar_historico(
                [{"concurso": 1, "numeros": [1] * 15}]
            )

    def test_each_prediction_receives_only_preceding_draws(self):
        historico = criar_historico(backtest_walk_forward.MINIMO_HISTORICO_TREINO + 1)
        vistos = []
        portfolio = [
            [((offset + numero) % 25) + 1 for numero in range(15)]
            for offset in range(20)
        ]

        def gerar(treino, concurso_alvo, seed):
            vistos.append((len(treino), treino[-1]["concurso"], concurso_alvo))
            return portfolio

        with patch.object(
            backtest_walk_forward,
            "_gerar_portfolio_modelo",
            side_effect=gerar,
        ):
            resultado = backtest_walk_forward.executar_backtest(
                historico,
                ultimos=1,
                replicas_aleatorias=1,
            )

        self.assertEqual(
            vistos,
            [(backtest_walk_forward.MINIMO_HISTORICO_TREINO,
              backtest_walk_forward.MINIMO_HISTORICO_TREINO,
              backtest_walk_forward.MINIMO_HISTORICO_TREINO + 1)],
        )
        self.assertEqual(resultado["concursos_avaliados"], 1)
        self.assertEqual(resultado["quantidade_jogos"], 20)

    def test_reports_exact_13_14_hits_and_portfolio_rates(self):
        historico = criar_historico(backtest_walk_forward.MINIMO_HISTORICO_TREINO + 1)
        resultado_alvo = historico[-1]["numeros"]
        portfolio_13 = criar_portfolio_com_acertos(resultado_alvo, 13)
        portfolio_14 = criar_portfolio_com_acertos(resultado_alvo, 14)

        with (
            patch.object(
                backtest_walk_forward,
                "_gerar_portfolio_modelo",
                return_value=portfolio_13,
            ),
            patch.object(
                backtest_walk_forward,
                "gerar_portfolio_aleatorio",
                return_value=portfolio_14,
            ),
        ):
            resultado = backtest_walk_forward.executar_backtest(
                historico,
                ultimos=1,
                replicas_aleatorias=1,
            )

        self.assertEqual(resultado["acertos_13_exatos_modelo_por_1000"], 1000)
        self.assertEqual(resultado["acertos_14_exatos_modelo_por_1000"], 0)
        self.assertEqual(resultado["acertos_13_exatos_aleatorio_por_1000"], 0)
        self.assertEqual(resultado["acertos_14_exatos_aleatorio_por_1000"], 1000)
        self.assertEqual(resultado["carteiras_com_13_ou_14_modelo_por_100"], 100)
        self.assertEqual(resultado["carteiras_com_13_ou_14_aleatorio_por_100"], 100)

    def test_rejects_portfolios_with_duplicate_tickets(self):
        with self.assertRaises(RuntimeError):
            jogo = list(range(1, 16))
            backtest_walk_forward.validar_portfolio([jogo, jogo.copy()], 2)


if __name__ == "__main__":
    unittest.main()
