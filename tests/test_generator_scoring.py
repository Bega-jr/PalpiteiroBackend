import unittest

from scripts.gerar_palpites_diarios import score_base


class GeneratorScoringTests(unittest.TestCase):
    def test_score_base_uses_the_structural_pattern_key(self):
        jogo = list(range(1, 16))
        chave = (120, 6, 6, (4, 4, 4, 0, 0))

        self.assertEqual(score_base(jogo, {chave: 0.75}), (0.75, 0.75, 0.75))

    def test_score_base_uses_neutral_value_for_unknown_pattern(self):
        self.assertEqual(score_base(list(range(1, 16)), {}), (0.5, 0.5, 0.5))


if __name__ == "__main__":
    unittest.main()
