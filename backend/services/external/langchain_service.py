from typing import Any, Optional

from langchain.hub import pull
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from models.ai.ai_request import AIRequestModel


class LangChainRequest(BaseModel):
    model_name: AIRequestModel = Field(
        ...,
        description="AI model to use as an AIRequestModel enum",
    )
    prompt_template: str = Field(
        ...,
        description="Name of the prompt from LangChain Hub (e.g., 'hwchase17/structured-chat')",
    )
    custom_prompt: Optional[str] = Field(
        default=None,
        description="Custom prompt template to use instead of a hub prompt",
    )
    input_variables: dict[str, Any] = Field(
        ..., description="Variables to be passed to the prompt template"
    )
    temperature: float = Field(
        default=0.7, description="Temperature for model generation"
    )
    max_tokens: Optional[int] = Field(
        default=5000, description="Maximum number of tokens to generate"
    )


class LangChainService:
    def __init__(self):
        self.output_parser = StrOutputParser()
        self.model_map = {
            "openai": ChatOpenAI,
            "anthropic": ChatAnthropic,
        }
        # Map AIRequestModel to provider and actual model name
        self.ai_model_mapping = {
            AIRequestModel.GPT_4_1: {"provider": "openai", "model_name": "gpt-4.1"},
            AIRequestModel.GPT_4_1_MINI: {
                "provider": "openai",
                "model_name": "gpt-4.1-mini",
            },
            AIRequestModel.GPT_4_1_NANO: {
                "provider": "openai",
                "model_name": "gpt-4.1-nano",
            },
            AIRequestModel.CLAUDE_3_7_SONNET: {
                "provider": "anthropic",
                "model_name": "claude-3-7-sonnet-20250219",
            },
            AIRequestModel.CLAUDE_3_5_HAIKU: {
                "provider": "anthropic",
                "model_name": "claude-3-5-haiku-20241022",
            },
        }

    async def _get_model(self, request: LangChainRequest):
        try:
            # Get provider from request directly if provided, otherwise determine from model enum
            if hasattr(request, "provider") and request.provider:
                provider = request.provider.lower()
            else:
                if request.model_name not in self.ai_model_mapping:
                    raise ValueError(f"Unsupported model: {request.model_name}")
                provider = self.ai_model_mapping[request.model_name]["provider"]

            model_class = self.model_map.get(provider)
            if not model_class:
                raise ValueError(f"Unsupported provider: {provider}")

            # Use the actual model name from the mapping
            if request.model_name not in self.ai_model_mapping:
                raise ValueError(f"Unsupported model: {request.model_name}")
            actual_model_name = self.ai_model_mapping[request.model_name]["model_name"]

            model_kwargs = {
                "model_name": actual_model_name,
                "temperature": request.temperature,
            }

            if request.max_tokens:
                model_kwargs["max_tokens"] = request.max_tokens

            return model_class(**model_kwargs)
        except Exception as e:
            raise ValueError(f"Error initializing model: {e!s}") from e

    async def process_request(self, request: LangChainRequest) -> dict[str, Any]:
        try:
            # Use custom prompt if provided, otherwise pull from hub
            if request.custom_prompt:
                prompt = ChatPromptTemplate.from_template(request.custom_prompt)
            else:
                # Pull prompt from hub (synchronously since pull is not async)
                prompt = pull(request.prompt_template)
                if not isinstance(prompt, ChatPromptTemplate):
                    prompt = ChatPromptTemplate.from_template(str(prompt))

            # Get model
            model = await self._get_model(request)

            # Create chain
            chain = prompt | model | self.output_parser

            # Process the request using arun for async execution
            result = await chain.ainvoke(request.input_variables)

            # Determine provider from the model mapping
            provider = self.ai_model_mapping[request.model_name]["provider"]

            return {
                "status": "success",
                "result": result,
                "model": str(request.model_name.value),
                "provider": provider,
            }

        except Exception as e:
            # Safely get provider if possible
            try:
                provider = (
                    self.ai_model_mapping[request.model_name]["provider"]
                    if request.model_name in self.ai_model_mapping
                    else "unknown"
                )
            except Exception:
                provider = "unknown"

            return {
                "status": "error",
                "error": str(e),
                "model": (
                    str(request.model_name.value)
                    if hasattr(request, "model_name")
                    else "unknown"
                ),
                "provider": provider,
            }


# Create singleton instance
langchain_service = LangChainService()
