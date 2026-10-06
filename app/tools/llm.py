"""Shared chat model factory. Picks the provider from settings.llm_provider."""

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings


@lru_cache
def get_llm(temperature: float = 0) -> BaseChatModel:
    if settings.llm_provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.llm_model,
            api_key=settings.groq_api_key,
            temperature=temperature,
        )

    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=settings.llm_model,
        api_key=settings.anthropic_api_key,
        temperature=temperature,
    )
