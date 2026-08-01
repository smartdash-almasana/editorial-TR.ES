"""Gemini REST adapter for schema-constrained JSON generation."""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Mapping
from urllib import error, parse, request


JsonTransport = Callable[[str, Mapping[str, str], bytes, float], Mapping[str, Any]]


class GeminiStructuredLLMAdapter:
    """Provider adapter using Gemini generateContent with structured outputs."""

    provider_id = "google-gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-3.6-flash",
        timeout_seconds: float = 90.0,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        transport: JsonTransport | None = None,
    ) -> None:
        normalized_key = api_key.strip() if api_key else ""
        normalized_model = model.strip() if model else ""
        if not normalized_key:
            raise ValueError("Gemini requiere una API key.")
        if not normalized_model:
            raise ValueError("Gemini requiere un model_id.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds debe ser positivo.")
        self._api_key = normalized_key
        self.model_id = normalized_model
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url.rstrip("/")
        self._transport = transport or self._urlopen_transport

    @classmethod
    def from_env(cls) -> "GeminiStructuredLLMAdapter":
        api_key = os.environ.get("GEMINI_API_KEY", "")
        model = os.environ.get("EDITORIAL_TRES_GEMINI_MODEL", "gemini-3.6-flash")
        timeout = float(os.environ.get("EDITORIAL_TRES_GEMINI_TIMEOUT_SECONDS", "90"))
        return cls(api_key=api_key, model=model, timeout_seconds=timeout)

    def generate_json(
        self,
        *,
        prompt: str,
        schema: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        normalized_prompt = prompt.strip() if prompt else ""
        if not normalized_prompt:
            raise ValueError("El prompt no puede estar vacío.")
        if not schema:
            raise ValueError("La salida estructurada requiere JSON Schema.")

        endpoint = (
            f"{self.base_url}/models/{parse.quote(self.model_id, safe='')}:generateContent"
        )
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": normalized_prompt}],
                }
            ],
            "generationConfig": {
                "responseFormat": {
                    "text": {
                        "mimeType": "application/json",
                        "schema": dict(schema),
                    }
                }
            },
        }
        response = self._transport(
            endpoint,
            headers,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            self.timeout_seconds,
        )
        text = self._extract_text(response)
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("Gemini devolvió texto que no es JSON válido.") from exc
        if not isinstance(decoded, dict):
            raise ValueError("Gemini debe devolver un objeto JSON en la raíz.")
        return decoded

    @staticmethod
    def _extract_text(response: Mapping[str, Any]) -> str:
        try:
            candidates = response["candidates"]
            parts = candidates[0]["content"]["parts"]
            text_parts = [part["text"] for part in parts if part.get("text")]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Respuesta Gemini sin contenido textual utilizable.") from exc
        text = "".join(text_parts).strip()
        if not text:
            raise ValueError("Gemini devolvió una respuesta textual vacía.")
        return text

    @staticmethod
    def _urlopen_transport(
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        timeout_seconds: float,
    ) -> Mapping[str, Any]:
        http_request = request.Request(
            url,
            data=body,
            headers=dict(headers),
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Gemini respondió HTTP {exc.code}: {details[:1000]}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"No se pudo conectar con Gemini: {exc.reason}") from exc

        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Gemini devolvió una respuesta HTTP no JSON.") from exc
        if not isinstance(decoded, dict):
            raise RuntimeError("Gemini devolvió una raíz HTTP no válida.")
        return decoded
