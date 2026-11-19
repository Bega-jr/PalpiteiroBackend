import contextlib
import io
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts import auditoria_estrutural, backup_analytics, snapshot_telemetria


class AnalyticsScriptExitCodeTests(unittest.TestCase):
    def test_structural_audit_returns_nonzero_when_a_table_fails(self):
        with (
            patch.object(auditoria_estrutural, "get_supabase"),
            patch.object(auditoria_estrutural, "TABELAS_CRITICAS", {"example": []}),
            patch.object(auditoria_estrutural, "auditar_tabela", return_value=False),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(auditoria_estrutural.main(), 1)

    def test_structural_audit_returns_zero_when_all_tables_pass(self):
        with (
            patch.object(auditoria_estrutural, "get_supabase"),
            patch.object(auditoria_estrutural, "TABELAS_CRITICAS", {"example": []}),
            patch.object(auditoria_estrutural, "auditar_tabela", return_value=True),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(auditoria_estrutural.main(), 0)

    def test_backup_returns_nonzero_when_a_table_export_fails(self):
        with (
            patch.object(backup_analytics, "get_supabase"),
            patch.object(backup_analytics, "TABELAS_BACKUP", ["example"]),
            patch.object(
                backup_analytics,
                "garantir_pasta",
                return_value=Path("backups"),
            ),
            patch.object(backup_analytics, "exportar_tabela", return_value=False),
            patch.object(backup_analytics, "limpar_backups_antigos"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(backup_analytics.main(), 1)

    def test_backup_returns_zero_when_all_table_exports_pass(self):
        with (
            patch.object(backup_analytics, "get_supabase"),
            patch.object(backup_analytics, "TABELAS_BACKUP", ["example"]),
            patch.object(
                backup_analytics,
                "garantir_pasta",
                return_value=Path("backups"),
            ),
            patch.object(backup_analytics, "exportar_tabela", return_value=True),
            patch.object(backup_analytics, "limpar_backups_antigos"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(backup_analytics.main(), 0)

    def test_snapshot_returns_nonzero_when_persistence_fails(self):
        query = Mock()
        query.select.return_value.order.return_value.limit.return_value.execute.return_value = (
            SimpleNamespace(data=[{"concurso_referencia": 3834}])
        )
        query.insert.return_value.execute.side_effect = RuntimeError("write failed")
        supabase = Mock()
        supabase.table.return_value = query

        with (
            patch.object(snapshot_telemetria, "get_supabase", return_value=supabase),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(snapshot_telemetria.main(), 1)

    def test_snapshot_returns_zero_when_persistence_succeeds(self):
        query = Mock()
        query.select.return_value.order.return_value.limit.return_value.execute.return_value = (
            SimpleNamespace(data=[{"concurso_referencia": 3834}])
        )
        supabase = Mock()
        supabase.table.return_value = query

        with (
            patch.object(snapshot_telemetria, "get_supabase", return_value=supabase),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(snapshot_telemetria.main(), 0)


if __name__ == "__main__":
    unittest.main()
