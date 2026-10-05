"""Shared Anthropic chat model factory."""

from functools import lru_cache

from langchain_anthropic import ChatAnthropic

from app.config import settings


@lru_cache
def get_llm(temperature: float = 0) -> ChatAnthropic:
    return ChatAnthropic(
        model=settings.llm_model,
        api_key=settings.anthropic_api_key,
        temperature=temperature,
    )
