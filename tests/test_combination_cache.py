import unittest

from app.services.estatisticas_combinacao_v3 import _parse_cache_key


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


if __name__ == "__main__":
    unittest.main()
