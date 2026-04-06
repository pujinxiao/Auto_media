from __future__ import annotations

import hashlib
import logging

from abc import ABC, abstractmethod
from typing import Any, Iterable, Mapping, Tuple


logger = logging.getLogger(__name__)


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(str(item.get("text", "")))
            else:
                chunks.append(str(item))
        return "\n".join(chunk for chunk in chunks if chunk)
    return str(content)


def estimate_tokens(payload: str | dict[str, Any] | Iterable[dict[str, Any]]) -> int:
    if isinstance(payload, str):
        normalized = payload.strip()
        return max(1, len(normalized) // 2) if normalized else 0
    if isinstance(payload, dict):
        return estimate_tokens(_message_text(payload))
    return sum(estimate_tokens(item) for item in payload)


def estimate_cacheable_prefix_tokens(
    *,
    system: str = "",
    messages: list[dict[str, Any]] | None = None,
) -> int:
    stable_token_budget = estimate_tokens({"role": "system", "content": system}) if system else 0
    for message in messages or []:
        stable_token_budget += estimate_tokens(message)
        if message.get("cacheable"):
            break
    return stable_token_budget


def build_cache_routing_key(
    *,
    provider: str,
    model: str,
    system: str = "",
    messages: list[dict[str, Any]] | None = None,
    cache_key: str = "",
) -> str:
    normalized_key = str(cache_key or "").strip()
    if normalized_key:
        return normalized_key[:128]

    stable_parts: list[str] = []
    if system:
        stable_parts.append(f"[SYSTEM]\n{system.strip()}")
    for message in messages or []:
        text = _message_text(message).strip()
        if text:
            role = str(message.get("role", "user")).upper()
            stable_parts.append(f"[{role}]\n{text}")
        if message.get("cacheable"):
            break
    if not stable_parts:
        return ""
    digest = hashlib.sha1("\n\n".join(stable_parts).encode("utf-8")).hexdigest()
    return f"{provider}:{model}:{digest}"[:128]


def build_message_blocks(content: Any, *, cacheable: bool = False) -> list[dict[str, Any]]:
    if isinstance(content, list):
        blocks: list[dict[str, Any]] = []
        for item in content:
            if isinstance(item, dict):
                block = dict(item)
                if block.get("type") == "text":
                    block["text"] = str(block.get("text", ""))
                    if cacheable and block["text"]:
                        block.setdefault("cache_control", {"type": "ephemeral"})
                blocks.append(block)
                continue

            text = str(item)
            block = {"type": "text", "text": text}
            if cacheable and text:
                block["cache_control"] = {"type": "ephemeral"}
            blocks.append(block)
        return blocks

    text = str(content or "")
    block = {"type": "text", "text": text}
    if cacheable and text:
        block["cache_control"] = {"type": "ephemeral"}
    return [block]


class BaseLLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        telemetry_context: Mapping[str, Any] | None = None,
    ) -> str:
        """Send a prompt and return the text response."""
        ...

    @abstractmethod
    async def complete_with_usage(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        telemetry_context: Mapping[str, Any] | None = None,
    ) -> Tuple[str, dict]:
        """
        Send a prompt and return both text response and usage information.

        Returns:
            Tuple[str, dict]: (text_response, {"prompt_tokens": int, "completion_tokens": int})
        """
        ...

    async def complete_messages(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        temperature: float = 0.3,
        enable_caching: bool = False,
        cache_key: str = "",
        cache_threshold_tokens: int = 1024,
        telemetry_context: Mapping[str, Any] | None = None,
    ) -> str:
        text, _ = await self.complete_messages_with_usage(
            messages=messages,
            system=system,
            temperature=temperature,
            enable_caching=enable_caching,
            cache_key=cache_key,
            cache_threshold_tokens=cache_threshold_tokens,
            telemetry_context=telemetry_context,
        )
        return text

    async def complete_messages_with_usage(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        temperature: float = 0.3,
        enable_caching: bool = False,
        cache_key: str = "",
        cache_threshold_tokens: int = 1024,
        telemetry_context: Mapping[str, Any] | None = None,
    ) -> Tuple[str, dict]:
        del enable_caching, cache_key, cache_threshold_tokens
        if not messages:
            message = (
                "BaseLLMProvider.complete_messages_with_usage requires at least one message; "
                "refusing to call complete_with_usage with an empty user prompt."
            )
            logger.warning(message)
            raise ValueError(message)

        if len(messages) == 1 and messages[0].get("role") == "user":
            user = _message_text(messages[0])
        else:
            user = "\n\n".join(
                f"[{str(message.get('role', 'user')).upper()}]\n{_message_text(message)}"
                for message in messages
                if _message_text(message)
            )
        return await self.complete_with_usage(
            system,
            user,
            temperature,
            telemetry_context=telemetry_context,
        )
