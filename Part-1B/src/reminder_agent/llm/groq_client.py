"""Groq adapter for the extraction port (OpenAI-compatible chat completions API, stdlib HTTP only).

Same contract as the Anthropic adapter: the model only extracts intent and verbatim spans, gets no tools,
and never sees ``now``. The API key is read from the ``GROQ_API_KEY`` environment variable and never logged.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from reminder_agent.errors import LlmTimeout, LlmUnavailable
from reminder_agent.llm.anthropic_client import SYSTEM_PROMPT, TIMEOUT_SECONDS, AnthropicExtractor
from reminder_agent.models import Ctx

DEFAULT_MODEL = "openai/gpt-oss-120b"
ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MAX_RETRIES = 4
HTTP_RATE_LIMITED = 429
MAX_TOKENS = 2048  # reasoning models spend part of the budget thinking; 512 left an empty answer


class GroqExtractor:
    """Extractor backed by Groq's chat completions endpoint."""

    def __init__(self, model: str | None = None, opener: Any = None) -> None:  # noqa: ANN401 - injectable for tests
        self._model = model or os.environ.get("REMINDER_LLM_MODEL", DEFAULT_MODEL)
        self._open = opener or urllib.request.urlopen
        self._payloads = AnthropicExtractor(client=object(), model=self._model)

    def build_request(self, message: str, ctx: Ctx, candidate_titles: list[str], feedback: str | None) -> dict:
        """Reuse the shared prompt/body builder, mapped onto the OpenAI-style payload. No tools, no ``now``."""
        base = self._payloads.build_request(message, ctx, candidate_titles, feedback)
        return {
            "model": self._model,
            "temperature": 0,
            "max_tokens": MAX_TOKENS,
            "reasoning_effort": "low",
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *base["messages"]],
        }

    def extract(self, message: str, ctx: Ctx, candidate_titles: list[str], feedback: str | None) -> str:
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise LlmUnavailable("no API key configured")
        body = json.dumps(self.build_request(message, ctx, candidate_titles, feedback)).encode()
        for attempt in range(MAX_RETRIES + 1):
            request = urllib.request.Request(  # noqa: S310 - fixed https endpoint
                ENDPOINT,
                data=body,
                method="POST",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "reminder-agent"},
            )
            try:
                with self._open(request, timeout=TIMEOUT_SECONDS) as reply:
                    data = json.loads(reply.read().decode("utf-8"))
                return str(data["choices"][0]["message"]["content"] or "")
            except urllib.error.HTTPError as exc:
                if exc.code == HTTP_RATE_LIMITED and attempt < MAX_RETRIES:
                    time.sleep(min(2 ** attempt * 2, 30))
                    continue
                raise LlmUnavailable(f"http {exc.code}") from exc
            except TimeoutError as exc:
                raise LlmTimeout("timeout") from exc
            except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
                raise LlmUnavailable("request failed") from exc
        raise LlmUnavailable("rate limited")  # pragma: no cover - loop always returns or raises
