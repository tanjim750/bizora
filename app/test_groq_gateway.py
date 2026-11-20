import io
import json
import os
import urllib.error
from unittest.mock import patch

from django.test import SimpleTestCase

from app.services.llm_gateway import execute_llm


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


class GroqGatewayTests(SimpleTestCase):
    def test_groq_response_maps_to_existing_provider_contract(self):
        response = {
            "model": "openai/gpt-oss-20b",
            "choices": [{"message": {"content": "Verified evidence supports the answer."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 7, "total_tokens": 17},
        }
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_API_KEYS": ""}, clear=False):
            with patch("urllib.request.urlopen", return_value=_Response(response)) as urlopen:
                result = execute_llm(prompt="Use verified facts", business_id=1, timeout_seconds=5)

        self.assertEqual(result["provider_status"], "ok")
        self.assertEqual(result["provider"], "groq")
        self.assertEqual(result["content"], "Verified evidence supports the answer.")
        self.assertEqual(result["tokens_used"], 17)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.groq.com/openai/v1/chat/completions")
        self.assertNotIn("test-key", request.data.decode())

    def test_multiple_keys_fail_over_without_leaking_credentials(self):
        denied = urllib.error.HTTPError("https://api.groq.com", 401, "Unauthorized", {}, io.BytesIO())
        response = {
            "model": "openai/gpt-oss-20b",
            "choices": [{"message": {"content": "Second key worked."}}],
            "usage": {},
        }
        with patch.dict(
            os.environ,
            {"GROQ_API_KEYS": "first-private-key,second-private-key", "GROQ_API_KEY": ""},
            clear=False,
        ):
            with patch("urllib.request.urlopen", side_effect=[denied, _Response(response)]) as urlopen:
                result = execute_llm(prompt="hello", business_id=1, timeout_seconds=5)

        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(result["content"], "Second key worked.")
        self.assertNotIn("private-key", str(result))

    def test_provider_error_returns_safe_fallback(self):
        denied = urllib.error.HTTPError("https://api.groq.com", 401, "Unauthorized", {}, io.BytesIO())
        with patch.dict(os.environ, {"GROQ_API_KEY": "private-key", "GROQ_API_KEYS": ""}, clear=False):
            with patch("urllib.request.urlopen", side_effect=denied):
                result = execute_llm(
                    prompt="hello",
                    business_id=1,
                    timeout_seconds=5,
                    fallback_response={"content": "Safe fallback"},
                )

        self.assertEqual(result["provider_status"], "error")
        self.assertEqual(result["content"], "Safe fallback")
        self.assertEqual(result["provider_error"], "Groq returned HTTP 401")
        self.assertNotIn("private-key", str(result))

    def test_missing_provider_preserves_unavailable_contract(self):
        with patch.dict(
            os.environ,
            {"GROQ_API_KEY": "", "GROQ_API_KEYS": "", "BIZORA_LLM_URL": ""},
            clear=False,
        ):
            result = execute_llm(
                prompt="hello",
                business_id=1,
                timeout_seconds=5,
                fallback_response={"content": "No provider"},
            )

        self.assertEqual(result["provider_status"], "unavailable")
        self.assertEqual(result["content"], "No provider")

    def test_reasoning_fallback_when_content_empty(self):
        response = {
            "model": "openai/gpt-oss-20b",
            "choices": [{"message": {"content": "", "reasoning": "Reasoning fallback answer."}}],
            "usage": {"total_tokens": 12},
        }
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_API_KEYS": ""}, clear=False):
            with patch("urllib.request.urlopen", return_value=_Response(response)):
                result = execute_llm(prompt="hello", business_id=1, timeout_seconds=5)

        self.assertEqual(result["provider_status"], "ok")
        self.assertEqual(result["content"], "Reasoning fallback answer.")

    def test_business_execute_llm_with_timeout_delegates(self):
        from app.models import Business

        business = Business(id=42, name="Test Biz")
        response = {
            "model": "openai/gpt-oss-20b",
            "choices": [{"message": {"content": "Delegated answer."}}],
            "usage": {"total_tokens": 8},
        }
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_API_KEYS": ""}, clear=False):
            with patch("urllib.request.urlopen", return_value=_Response(response)):
                result = business.execute_llm_with_timeout("Test prompt")

        self.assertEqual(result["provider_status"], "ok")
        self.assertEqual(result["content"], "Delegated answer.")
