import contextlib
import io
import unittest
from unittest.mock import patch

from app.services import meta_learning_service
from scripts import processamento_feedback_meta


class FakeSupabase:
    def __init__(self, existing_feedback):
        self.existing_feedback = existing_feedback
        self.operations = []

    def table(self, name):
        return FakeQuery(self, name)


class FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name

    def select(self, columns):
        self.supabase.operations.append((self.table_name, "select", columns))
        return self

    def eq(self, column, value):
        self.supabase.operations.append((self.table_name, "eq", column, value))
        return self

    def limit(self, value):
        self.supabase.operations.append((self.table_name, "limit", value))
        return self

    def execute(self):
        self.supabase.operations.append((self.table_name, "execute"))
        data = [{"concurso_referencia": 3833}] if self.supabase.existing_feedback else []
        return type("Response", (), {"data": data})()


class MetaLearningIdempotencyTests(unittest.TestCase):
    def test_existing_contest_feedback_is_not_applied_twice(self):
        supabase = FakeSupabase(existing_feedback=True)
        with (
            patch.object(meta_learning_service, "get_supabase", return_value=supabase),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            updated = meta_learning_service.atualizar_meta_learning(
                media_acertos=8.6,
                concurso_ref=3833,
                melhor_acerto=11,
                pior_acerto=7,
                dispersao=4,
                qtd_palpites=20,
            )

        self.assertFalse(updated)
        self.assertEqual(
            [operation[0] for operation in supabase.operations],
            ["meta_learning_execucoes"] * 4,
        )

    def test_manual_feedback_skips_contest_already_processed(self):
        supabase = FakeSupabase(existing_feedback=True)
        with (
            patch.object(processamento_feedback_meta, "get_supabase", return_value=supabase),
            patch.object(
                processamento_feedback_meta,
                "carregar_historico",
                return_value=[{"concurso": 3833, "numeros": list(range(1, 16))}],
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            processamento_feedback_meta.avaliar_desempenho_concurso()

        self.assertEqual(
            [operation[0] for operation in supabase.operations],
            ["meta_learning_execucoes"] * 4,
        )


if __name__ == "__main__":
    unittest.main()
