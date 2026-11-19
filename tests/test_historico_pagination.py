import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.historico_service import listar_historico


class HistoricoPaginationTests(unittest.TestCase):
    @patch("app.services.historico_service.get_supabase")
    def test_lists_requested_page(self, get_supabase):
        query = MagicMock()
        query.execute.return_value.data = [{"id": "game-1"}]
        (
            get_supabase.return_value.table.return_value
            .select.return_value.eq.return_value.order.return_value.range.return_value
        ) = query

        result = listar_historico(uuid4(), page=3, limit=20)

        self.assertEqual(result, [{"id": "game-1"}])
        query.range.assert_not_called()
        (
            get_supabase.return_value.table.return_value
            .select.return_value.eq.return_value.order.return_value.range
        ).assert_called_once_with(40, 59)

    def test_rejects_invalid_pagination(self):
        with self.assertRaises(ValueError):
            listar_historico(uuid4(), page=0, limit=20)


if __name__ == "__main__":
    unittest.main()
