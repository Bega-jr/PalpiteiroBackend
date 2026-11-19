import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.services.estatisticas_combinacao_v3 import (
    CACHE_VERSION,
    _parse_cache_key,
    carregar_cache,
    calcular_score_combinacoes_reais,
    salvar_cache,
)


class CombinationCacheTests(unittest.TestCase):
    def test_parse_cache_key_accepts_expected_structural_tuple(self):
        key = "(180, 6, 6, (3, 3, 3, 3, 3))"

        self.assertEqual(
            _parse_cache_key(key),
            (180, 6, 6, (3, 3, 3, 3, 3)),
        )

    def test_parse_cache_key_rejects_executable_expression(self):
        with self.assertRaises((SyntaxError, ValueError)):
            _parse_cache_key("__import__('os').system('false')")

    def test_parse_cache_key_rejects_invalid_shape(self):
        with self.assertRaises(ValueError):
            _parse_cache_key("(180, 6, 6, (3, 3))")

    def test_as_of_scores_use_only_supplied_history_without_cache_or_database(self):
        historico = [
            {"concurso": 1, "numeros": list(range(1, 16))},
            {"concurso": 2, "numeros": list(range(2, 17))},
        ]

        with (
            patch(
                "app.services.estatisticas_combinacao_v3.get_supabase",
                side_effect=AssertionError("O backtest não deve consultar o banco."),
            ),
            patch("app.services.estatisticas_combinacao_v3.salvar_cache") as salvar_cache,
        ):
            scores, metadata = calcular_score_combinacoes_reais(
                historico=historico
            )

        self.assertTrue(scores)
        self.assertEqual(set(scores), set(metadata))
        salvar_cache.assert_not_called()

    def test_cache_is_saved_atomically_and_can_be_loaded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "nested" / "patterns.json"
            payload = {
                "cache_version": CACHE_VERSION,
                "limite_concursos": 1000,
                "scores": {},
                "metadata": {},
            }

            with patch(
                "app.services.estatisticas_combinacao_v3.CACHE_FILE",
                cache_path,
            ):
                salvar_cache(payload)
                self.assertEqual(carregar_cache(), payload)
                self.assertEqual(list(cache_path.parent.iterdir()), [cache_path])

    def test_cached_scores_are_not_reused_for_another_history_limit(self):
        cache_key = "(180, 6, 6, (3, 3, 3, 3, 3))"
        stale_cache = {
            "cache_version": CACHE_VERSION,
            "limite_concursos": 1,
            "scores": {cache_key: 99.0},
            "metadata": {cache_key: {"freq": 99}},
        }
        query = unittest.mock.MagicMock()
        query.execute.return_value.data = [
            {"dezenas": list(range(1, 16))},
            {"dezenas": list(range(2, 17))},
        ]
        supabase = unittest.mock.MagicMock()
        supabase.table.return_value.select.return_value.order.return_value.limit.return_value = query

        with (
            patch(
                "app.services.estatisticas_combinacao_v3.carregar_cache",
                return_value=stale_cache,
            ),
            patch(
                "app.services.estatisticas_combinacao_v3.get_supabase",
                return_value=supabase,
            ),
            patch("app.services.estatisticas_combinacao_v3.salvar_cache"),
        ):
            scores, _ = calcular_score_combinacoes_reais(
                limite_concursos=2,
                usar_cache=True,
            )

        self.assertNotEqual(scores.get(_parse_cache_key(cache_key)), 99.0)
        supabase.table.assert_called_once_with("lotofacil_concursos")

    def test_rejects_non_positive_history_limit(self):
        with self.assertRaises(ValueError):
            calcular_score_combinacoes_reais(limite_concursos=0)


if __name__ == "__main__":
    unittest.main()
