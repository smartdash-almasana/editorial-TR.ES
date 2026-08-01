import json

import pytest

from editorial_tres.infrastructure.gemini_structured_llm import GeminiStructuredLLMAdapter


def test_gemini_adapter_sends_schema_constrained_request_and_parses_json():
    captured = {}

    def transport(url, headers, body, timeout):
        captured.update(
            url=url,
            headers=headers,
            body=json.loads(body.decode("utf-8")),
            timeout=timeout,
        )
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": '{"clusters": []}'}
                        ]
                    }
                }
            ]
        }

    adapter = GeminiStructuredLLMAdapter(
        api_key="secret-key",
        model="gemini-3.6-flash",
        timeout_seconds=12,
        transport=transport,
    )
    schema = {
        "type": "object",
        "properties": {"clusters": {"type": "array", "items": {"type": "object"}}},
        "required": ["clusters"],
    }

    result = adapter.generate_json(prompt="Analizá el manuscrito.", schema=schema)

    assert result == {"clusters": []}
    assert captured["url"].endswith("/models/gemini-3.6-flash:generateContent")
    assert captured["headers"]["x-goog-api-key"] == "secret-key"
    assert captured["timeout"] == 12
    assert captured["body"]["contents"][0]["parts"][0]["text"] == "Analizá el manuscrito."
    response_format = captured["body"]["generationConfig"]["responseFormat"]["text"]
    assert response_format["mimeType"] == "application/json"
    assert response_format["schema"] == schema
    assert "temperature" not in captured["body"]["generationConfig"]


def test_gemini_adapter_rejects_non_json_model_output():
    def transport(url, headers, body, timeout):
        return {
            "candidates": [
                {"content": {"parts": [{"text": "no es json"}]}}
            ]
        }

    adapter = GeminiStructuredLLMAdapter(api_key="secret", transport=transport)

    with pytest.raises(ValueError, match="no es JSON válido"):
        adapter.generate_json(
            prompt="Analizá.",
            schema={"type": "object"},
        )


def test_gemini_adapter_requires_api_key():
    with pytest.raises(ValueError, match="API key"):
        GeminiStructuredLLMAdapter(api_key="")
