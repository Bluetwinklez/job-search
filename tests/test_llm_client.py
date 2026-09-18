import unittest
from unittest.mock import MagicMock, patch
import json

from app.llm_client import (
    PROVIDERS,
    get_available_providers,
    generate_llm_response,
    call_anthropic,
    call_openai,
    call_gemini,
)


class TestLLMClient(unittest.TestCase):
    def test_providers_structure(self):
        self.assertIn("anthropic", PROVIDERS)
        self.assertIn("openai", PROVIDERS)
        self.assertIn("gemini", PROVIDERS)
        self.assertTrue(len(PROVIDERS["anthropic"]["models"]) > 0)

    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                call_anthropic("hello", api_key="")
            with self.assertRaises(ValueError):
                call_openai("hello", api_key="")
            with self.assertRaises(ValueError):
                call_gemini("hello", api_key="")

    @patch("urllib.request.urlopen")
    def test_call_openai_mock(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "OpenAI cevabi"}}]
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = call_openai("Prompt", api_key="sk-test-fake")
        self.assertEqual(res, "OpenAI cevabi")

    @patch("urllib.request.urlopen")
    def test_call_gemini_mock(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "candidates": [{
                "content": {"parts": [{"text": "Gemini cevabi"}]}
            }]
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = call_gemini("Prompt", api_key="gm-test-fake")
        self.assertEqual(res, "Gemini cevabi")

    def test_invalid_provider_raises(self):
        with self.assertRaises(ValueError):
            generate_llm_response("test", provider="unknown_provider")


if __name__ == "__main__":
    unittest.main()
