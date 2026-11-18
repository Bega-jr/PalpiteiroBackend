import contextlib
import io
import unittest
from unittest.mock import patch

from scripts import meta_validacao_final


class FakeSupabase:
    def __init__(self):
        self.operations = []

    def table(self, name):
        return FakeQuery(self.operations, name)


class FakeQuery:
    def __init__(self, operations, table):
        self.operations = operations
        self.table_name = table

    def upsert(self, payload, on_conflict=None):
        self.operations.append((self.table_name, "upsert", payload))
        return self

    def delete(self):
        self.operations.append((self.table_name, "delete"))
        return self

    def eq(self, column, value):
        self.operations.append((self.table_name, "eq", column, value))
        return self

    def gt(self, column, value):
        self.operations.append((self.table_name, "gt", column, value))
        return self

    def execute(self):
        self.operations.append((self.table_name, "execute"))
        return None


def make_result():
    palpites = [
        {
            "indice_palpite": index,
            "numeros": list(range(1, 16)),
            "score": 1.0,
            "score_potencial": 1.0,
            "score_montecarlo": 1.0,
            "score_estrutural": 1.0,
            "cluster_id": 1,
            "hash_estrutura": "3-3-3-3-3",
            "metricas": {},
            "filtros_aplicados": {},
        }
        for index in range(1, meta_validacao_final.QTD_FINAL + 1)
    ]
    return {
        "palpites": palpites,
        "concurso": 42,
        "linhas_telegram": [],
        "matriz": list(range(1, 19)),
        "cobertura_matriz": 1.0,
    }


class MetaValidationTests(unittest.TestCase):
    def test_rejected_portfolios_preserve_existing_predictions(self):
        supabase = FakeSupabase()
        with (
            patch.object(meta_validacao_final, "get_supabase", return_value=supabase),
            patch.object(meta_validacao_final, "executar_motor_geracao", return_value=make_result()),
            patch(
                "scripts.processamento_diario_lotofacil.carregar_historico",
                return_value=[{"concurso": 41}],
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = meta_validacao_final.main()

        self.assertEqual(result, 1)
        self.assertFalse(
            any(operation[0] == "palpites_validos" for operation in supabase.operations)
        )

    def test_approved_portfolio_is_persisted_after_validation(self):
        supabase = FakeSupabase()
        analysis = {
            "status": "OK",
            "overlap_medio": 9.0,
            "entropia": 4.0,
            "diversidade": 25,
            "risco_colapso": 0,
            "nivel_risco": "BAIXO",
            "dezenas_superexpostas": [],
            "alertas": [],
            "limite_exposicao_real": 15,
        }
        with (
            patch.object(meta_validacao_final, "get_supabase", return_value=supabase),
            patch.object(meta_validacao_final, "executar_motor_geracao", return_value=make_result()),
            patch.object(meta_validacao_final, "analisar_portfolio", return_value=analysis),
            patch.object(meta_validacao_final, "montar_msg_telegram", return_value="payload"),
            patch(
                "scripts.processamento_diario_lotofacil.carregar_historico",
                return_value=[{"concurso": 41}],
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = meta_validacao_final.main()

        self.assertEqual(result, 0)
        prediction_operations = [
            operation
            for operation in supabase.operations
            if operation[0] == "palpites_validos"
        ]
        self.assertEqual(
            [operation[1] for operation in prediction_operations],
            ["upsert", "execute", "delete", "eq", "gt", "execute"],
        )
        self.assertEqual(
            prediction_operations[3],
            ("palpites_validos", "eq", "concurso_referencia", 42),
        )
        self.assertEqual(
            prediction_operations[4],
            ("palpites_validos", "gt", "indice_palpite", 20),
        )

    def test_normalization_rejects_invalid_number_sets(self):
        with self.assertRaises(ValueError):
            meta_validacao_final.normalizar_palpites(
                [{"indice_palpite": 1, "numeros": [1, 1, 3]}]
            )

    def test_exposure_limit_allows_the_expected_portfolio_distribution(self):
        jogos = [
            {
                "numeros": [
                    ((offset + index) % 25) + 1
                    for index in range(15)
                ]
            }
            for offset in range(meta_validacao_final.QTD_FINAL)
        ]
        for offset in range(1, 8):
            jogos[offset]["numeros"][-1] = 1

        analysis = meta_validacao_final.analisar_portfolio(jogos)

        self.assertEqual(analysis["limite_exposicao_real"], 18)
        self.assertEqual(analysis["dezenas_superexpostas"], [])


if __name__ == "__main__":
    unittest.main()
