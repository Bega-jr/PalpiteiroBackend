import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.core import auth


class AuthCacheTests(unittest.TestCase):
    def setUp(self):
        with auth.cache_lock:
            auth.token_cache.clear()

    def tearDown(self):
        with auth.cache_lock:
            auth.token_cache.clear()

    @patch("app.core.auth.get_supabase")
    def test_valid_token_is_cached(self, get_supabase):
        user = SimpleNamespace(id="user-1", token_exp=time.time() + 60)
        get_supabase.return_value.auth.get_user.return_value.user = user

        first = auth.validate_token("token-1")
        second = auth.validate_token("token-1")

        self.assertIs(first, user)
        self.assertIs(second, user)
        get_supabase.return_value.auth.get_user.assert_called_once_with("token-1")

    def test_rejects_non_bearer_authorization_header(self):
        with self.assertRaises(HTTPException) as raised:
            auth.get_user("Basic token-1")

        self.assertEqual(raised.exception.status_code, 401)

    @patch("app.core.auth.get_supabase")
    def test_auth_service_failure_is_not_reported_as_invalid_token(self, get_supabase):
        get_supabase.return_value.auth.get_user.side_effect = RuntimeError("offline")

        with self.assertRaises(HTTPException) as raised:
            auth.validate_token("token-1")

        self.assertEqual(raised.exception.status_code, 503)

    def test_cache_size_is_bounded(self):
        with (
            patch("app.core.auth.MAX_TOKEN_CACHE_ENTRIES", 2),
            patch("app.core.auth.get_supabase") as get_supabase,
        ):
            get_supabase.return_value.auth.get_user.side_effect = [
                SimpleNamespace(user=SimpleNamespace(id="1", token_exp=time.time() + 60)),
                SimpleNamespace(user=SimpleNamespace(id="2", token_exp=time.time() + 60)),
                SimpleNamespace(user=SimpleNamespace(id="3", token_exp=time.time() + 60)),
            ]

            auth.validate_token("token-1")
            auth.validate_token("token-2")
            auth.validate_token("token-3")

        self.assertEqual(len(auth.token_cache), 2)
        self.assertNotIn("token-1", auth.token_cache)


if __name__ == "__main__":
    unittest.main()
