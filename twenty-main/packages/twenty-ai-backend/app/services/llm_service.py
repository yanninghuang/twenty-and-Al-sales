"""LLM service supporting DeepSeek, Anthropic Claude, and OpenAI."""

from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

# Anthropic is optional — only needed if using Claude models
try:
    from langchain_anthropic import ChatAnthropic
    HAS_ANTHROPIC = True
except ImportError:
    ChatAnthropic = None  # type: ignore
    HAS_ANTHROPIC = False

from app.core.config import settings


class LLMService:
    """Thin wrapper around LangChain chat models — supports DeepSeek, Claude, GPT."""

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> None:
        model_name = model or settings.default_llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens

        if model_name.startswith("deepseek"):
            # DeepSeek uses OpenAI-compatible API
            self.chat_model = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=settings.deepseek_api_key,  # type: ignore[arg-type]
                base_url=settings.deepseek_base_url,
            )
        elif model_name.startswith("claude"):
            if not HAS_ANTHROPIC:
                raise ImportError(
                    "langchain-anthropic is not installed. Install it with: pip install langchain-anthropic"
                )
            self.chat_model = ChatAnthropic(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=settings.anthropic_api_key,  # type: ignore[arg-type]
            )
        else:
            self.chat_model = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=settings.openai_api_key,  # type: ignore[arg-type]
            )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        messages_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a text completion."""
        message_list: list[BaseMessage] = [SystemMessage(content=system_prompt)]

        if messages_history:
            for msg in messages_history:
                if msg["role"] == "user":
                    message_list.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    message_list.append(AIMessage(content=msg["content"]))

        message_list.append(HumanMessage(content=user_prompt))
        response = await self.chat_model.ainvoke(message_list)
        content: str = (
            response.content if isinstance(response.content, str) else str(response.content)
        )
        return content

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate structured JSON output using tool/function calling."""
        structured_model = self.chat_model.with_structured_output(output_schema)
        message_list: list[BaseMessage] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        result = await structured_model.ainvoke(message_list)
        return result if isinstance(result, dict) else {}


# Singleton instances
def get_llm_service(
    model: str | None = None, temperature: float = 0.3, max_tokens: int = 4096
) -> LLMService:
    """Factory to create LLM service instances."""
    return LLMService(model=model, temperature=temperature, max_tokens=max_tokens)
