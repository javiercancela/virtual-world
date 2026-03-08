from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class LlamaTransportError(RuntimeError):
    """Raised when llama-server cannot be reached or returns malformed data."""


@dataclass(slots=True)
class LlamaServerClient:
    endpoint: str
    timeout_seconds: float = 20.0

    def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None = None,
        grammar: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if grammar is not None:
            payload["grammar"] = grammar
        return self._post_json(payload)

    def text_completion(
        self,
        *,
        model: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        grammar: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if grammar is not None:
            payload["grammar"] = grammar
        return self._post_json(payload)

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:

        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise LlamaTransportError(f"Unable to reach llama-server at {self.endpoint}: {exc}") from exc

        try:
            parsed = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise LlamaTransportError(f"llama-server returned invalid JSON: {exc}") from exc
        return parsed


def extract_chat_text(response_payload: dict[str, Any]) -> str:
    try:
        message = response_payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlamaTransportError("llama-server response did not include choices[0].message.") from exc

    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        joined = "".join(parts).strip()
        if joined:
            return joined
    raise LlamaTransportError("llama-server response did not include text content.")


def extract_completion_text(response_payload: dict[str, Any]) -> str:
    try:
        choice = response_payload["choices"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlamaTransportError("llama-server response did not include choices[0].") from exc

    text = choice.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return extract_chat_text(response_payload)
