import unittest

from scripts.gerar_palpites_diarios import (
    calcular_flags_popularidade,
    classificar_dezenas_populares,
)


class PopularityFlagTests(unittest.TestCase):
    def test_classifies_top_and_bottom_ten_from_last_ten_draws(self):
        historico = [
            {"concurso": concurso, "numeros": list(range(1, 16))}
            for concurso in range(1, 11)
        ]

        mais_sorteados, menos_sorteados = classificar_dezenas_populares(historico)

        self.assertEqual(mais_sorteados, set(range(1, 11)))
        self.assertEqual(menos_sorteados, set(range(16, 26)))

    def test_flags_indicate_any_number_from_each_frequency_group(self):
        mais_sorteados = set(range(1, 11))
        menos_sorteados = set(range(16, 26))

        self.assertEqual(
            calcular_flags_popularidade([2, 11], mais_sorteados, menos_sorteados),
            {"usa_mais_sorteados": True, "usa_menos_sorteados": False},
        )
        self.assertEqual(
            calcular_flags_popularidade([18, 12], mais_sorteados, menos_sorteados),
            {"usa_mais_sorteados": False, "usa_menos_sorteados": True},
        )
        self.assertEqual(
            calcular_flags_popularidade([11, 12], mais_sorteados, menos_sorteados),
            {"usa_mais_sorteados": False, "usa_menos_sorteados": False},
        )

    def test_requires_ten_historical_draws(self):
        with self.assertRaises(ValueError):
            classificar_dezenas_populares([{"concurso": 1, "numeros": list(range(1, 16))}])


if __name__ == "__main__":
    unittest.main()
