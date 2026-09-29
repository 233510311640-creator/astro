import unittest

from local_assistant.local_model import LocalModel


class LocalModelSecurityTests(unittest.TestCase):
    def test_loopback_is_allowed(self):
        model = LocalModel("http://127.0.0.1:8080", "test-model")
        self.assertEqual(model.base_url, "http://127.0.0.1:8080")
        self.assertEqual(model.model, "test-model")

    def test_lan_and_https_endpoints_are_blocked(self):
        with self.assertRaises(ValueError):
            LocalModel("http://192.168.1.5:8080")
        with self.assertRaises(ValueError):
            LocalModel("https://example.com")


if __name__ == "__main__":
    unittest.main()
