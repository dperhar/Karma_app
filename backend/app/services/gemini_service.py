import os
import logging
from typing import Optional, Dict, Any
import json
import time
import random
import asyncio
import requests
import google.generativeai as genai
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global concurrency guard (per-process)
_GEMINI_MAX_CONCURRENT = int(os.getenv("GEMINI_MAX_CONCURRENT", "2"))
_SEMAPHORE: Optional[asyncio.Semaphore]
try:
    _SEMAPHORE = asyncio.Semaphore(_GEMINI_MAX_CONCURRENT) if _GEMINI_MAX_CONCURRENT > 0 else None
except Exception:
    _SEMAPHORE = None

class GeminiService:
    def __init__(self):
        raw_key = os.getenv("GEMINI_API_KEY", "")
        raw_google = os.getenv("GEMINI_API_KEY_GOOGLE")
        raw_proxy = os.getenv("GEMINI_API_KEY_PROXY")
        # Back-compat: single key works for both; specific keys override per provider
        self.api_key = (raw_key or raw_google or raw_proxy or "").strip()
        self.api_key_google = (raw_google or raw_key or "").strip()
        self.api_key_proxy = (raw_proxy or raw_key or "").strip()
        # Base URL selection: Google default or proxy from settings
        base_url = (settings.GEMINI_BASE_URL or "https://generativelanguage.googleapis.com").rstrip("/")
        api_version = settings.GEMINI_API_VERSION or "v1beta"
        self.base_url = base_url
        self.api_version = api_version
        # Rate limit/backoff config
        self.max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "4"))
        self.backoff_base = float(os.getenv("GEMINI_BACKOFF_BASE", "1.8"))
        self.min_delay_ms = int(os.getenv("GEMINI_MIN_DELAY_MS", "150"))
        self.jitter_ms = int(os.getenv("GEMINI_JITTER_MS", "200"))
        if not (self.api_key_google or self.api_key_proxy):
            logger.warning("No GEMINI API key found (GEMINI_API_KEY / _GOOGLE / _PROXY). Using mock mode.")
            self.mock_mode = True
        else:
            try:
                # Initialize SDK path only if Google key is available
                if self.api_key_google:
                    logger.info(
                        f"Gemini Google API key loaded (length={len(self.api_key_google)}). Initializing client..."
                    )
                    genai.configure(api_key=self.api_key_google)
                    # Library client kept as a fallback
                    self.model = genai.GenerativeModel(
                        model_name='gemini-2.5-pro',
                        generation_config={
                            "temperature": 0.95,
                            "response_mime_type": "application/json",
                        },
                    )
                    self.chat = self.model.start_chat(history=[])
                else:
                    # REST only (proxy) – keep placeholders
                    self.model = None  # type: ignore[assignment]
                    self.chat = None   # type: ignore[assignment]
                self.mock_mode = False
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.mock_mode = True
        
    async def generate_comment(
        self,
        post_content: str,
        user_context: Dict[str, Any],
        channel_context: Dict[str, Any]
    ) -> str:
        try:
            if self.mock_mode:
                return f"Интересная мысль! Особенно понравилось про {post_content[:30]}... 🤔"
            prompt = f"""
            Сгенерируй комментарий к посту в Telegram канале.
            
            Контекст поста:
            {post_content}
            
            Контекст пользователя:
            {user_context}
            
            Контекст канала:
            {channel_context}
            
            Комментарий должен быть:
            1. Релевантным теме поста
            2. Соответствовать стилю общения пользователя
            3. Быть естественным и не похожим на бота
            4. Не длиннее 2-3 предложений
            """
            response = await self.chat.send_message_async(prompt)
            return getattr(response, "text", "").strip()
        except Exception as e:
            logger.error(f"Error generating comment with Gemini: {e}")
            raise 

    async def generate_content(self, prompt: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            if self.mock_mode:
                if "Vibe Profile" in prompt or "Analyze the following collection" in prompt:
                    return {
                        "success": True,
                        "content": json.dumps({
                            "tone": "casual and witty",
                            "verbosity": "moderate",
                            "emoji_usage": "light",
                            "common_phrases": ["lol", "that's wild", "makes sense"],
                            "topics_of_interest": ["AI", "startups", "tech news"]
                        })
                    }
                return {"success": True, "content": "This is a mock response."}

            # Resolve per-request overrides with environment defaults
            preferred_model = settings.GEMINI_MODEL_PROD if not settings.IS_DEVELOP else settings.GEMINI_MODEL_DEV
            model_name = (overrides or {}).get("model") or preferred_model or "gemini-2.5-pro"
            # Normalize model names for proxy compatibility, but keep a set of candidates to try
            proxy = "hubai" in self.base_url
            proxy_model_candidates = []
            if proxy:
                # Try a few likely models exposed by the proxy in order
                proxy_model_candidates = [
                    model_name,
                    "gemini-2.0-flash-lite",
                    "gemini-pro",
                    "gemini-1.5-pro",
                ]
            try:
                temperature = float((overrides or {}).get("temperature", self.model.generation_config.get("temperature", 0.95)))
            except Exception:
                temperature = 0.95
            try:
                max_output_tokens = int((overrides or {}).get("max_output_tokens", 4096))
            except Exception:
                max_output_tokens = 4096

            # Small pre-call delay to shape burstiness
            try:
                pre_delay = (self.min_delay_ms + random.randint(0, self.jitter_ms)) / 1000.0
                if pre_delay > 0:
                    await asyncio.sleep(pre_delay)
            except Exception:
                pass

            # Prefer REST call for deterministic behavior, honoring base URL and auth scheme
            async def _rest_call_with_model(model_attempt: str, temp: float, max_tokens: int) -> Dict[str, Any]:
                headers = {"Content-Type": "application/json"}
                # Provider selection precedence:
                # 1) Explicit override from caller (UI/user)
                # 2) Environment inference (auth scheme/base URL)
                provider_override = (overrides or {}).get("provider")
                scheme = (settings.GEMINI_AUTH_SCHEME or "auto").lower()
                if provider_override == "google":
                    use_proxy = False
                elif provider_override == "proxy":
                    use_proxy = True
                else:
                    use_proxy = (scheme == "bearer") or (scheme == "auto" and "hubai" in self.base_url)
                if use_proxy:
                    key = self.api_key_proxy or self.api_key
                    if not key:
                        return {"success": False, "error": "Missing proxy API key"}
                    headers["Authorization"] = f"Bearer {key}"
                else:
                    key = self.api_key_google or self.api_key
                    if not key:
                        return {"success": False, "error": "Missing Google API key"}
                    headers["X-goog-api-key"] = key
                # Force JSON mode by wrapping prompt; Gemini sometimes returns code fences regardless of mime type
                prompt_wrapped = (
                    "Return ONLY a single valid JSON object. Do not include code fences or any prose before/after.\n" + prompt
                )
                body = {
                    "contents": [{"parts": [{"text": prompt_wrapped}]}],
                    "generationConfig": {
                        "temperature": temp,
                        "maxOutputTokens": max_tokens,
                        # Hint Gemini REST to return strict JSON
                        "responseMimeType": "application/json",
                    },
                    # Relax safety to avoid empty blocks while we post-process anyway
                    "safetySettings": [
                        {"category": "HARM_CATEGORY_SEXUAL", "threshold": "BLOCK_ONLY_HIGH"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
                    ],
                }
                # Route selection: Google uses models/*:generateContent, some proxies expose OpenAI-like /chat/completions
                if use_proxy:
                    # OpenAI-compatible proxy
                    rest_url = f"{self.base_url}/{settings.GEMINI_API_VERSION}/chat/completions"
                    body = {
                        "model": model_attempt,
                        "messages": [{"role": "user", "content": prompt_wrapped}],
                        "temperature": temp,
                        "max_tokens": max_tokens,
                        "response_format": {"type": "json_object"},
                    }
                else:
                    rest_url = f"{self.base_url}/{self.api_version}/models/{model_attempt}:generateContent"
                resp = requests.post(rest_url, json=body, headers=headers, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    # Parse Google response
                    if "candidates" in data:
                        text_segments: list[str] = []
                        for cand in data.get("candidates", [])[:1]:
                            content = cand.get("content", {})
                            for part in content.get("parts", []):
                                t = part.get("text")
                                if t:
                                    text_segments.append(t)
                        content_text = "".join(text_segments).strip()
                        # If empty due to safety block, surface a reason
                        if not content_text:
                            block_reason = (data.get("promptFeedback", {}) or {}).get("blockReason")
                            if block_reason:
                                return {"success": False, "error": f"Blocked: {block_reason}", "status": 200}
                        # Defensive: if Gemini still returns code fences, strip them here
                        if content_text.startswith("```"):
                            try:
                                fence_end = content_text.rfind("```")
                                inner = content_text[3:fence_end] if fence_end != -1 else content_text[3:]
                                if inner.lower().startswith("json"):
                                    inner = inner[4:]
                                content_text = inner.strip()
                            except Exception:
                                pass
                    else:
                        # Parse OpenAI-like proxy response
                        choices = data.get("choices") or []
                        if choices and isinstance(choices[0], dict):
                            msg = choices[0].get("message") or {}
                            content_text = (msg.get("content") or "").strip()
                        else:
                            content_text = ""
                    if content_text:
                        return {"success": True, "content": content_text}
                    return {"success": False, "error": "Empty content"}
                # Handle rate limit and transient errors
                if resp.status_code in (429, 500, 502, 503, 504):
                    return {"success": False, "error": resp.text, "status": resp.status_code, "retry_after": resp.headers.get("retry-after")}
                # Other errors
                logger.error("Gemini REST error %s: %s", resp.status_code, resp.text[:500])
                return {"success": False, "error": resp.text, "status": resp.status_code}

            # Retry strategy with model fallbacks and safer decoding
            model_candidates = [
                (model_name, temperature, max_output_tokens),
            ]
            if settings.GEMINI_ENABLE_FALLBACKS:
                model_candidates += [
                    ("gemini-1.5-pro", 0.4, min(768, max_output_tokens)),
                    ("gemini-1.5-flash", 0.3, min(640, max_output_tokens)),
                ]
            # If proxy, prepend alternative proxy model ids to try
            if proxy and proxy_model_candidates:
                model_candidates = [
                    (mn, temperature, max_output_tokens) for mn in proxy_model_candidates
                ] + model_candidates
            attempts = self.max_retries
            for attempt in range(1, attempts + 1):
                for m_name, temp_try, max_tok_try in model_candidates:
                    if _SEMAPHORE is not None:
                        async with _SEMAPHORE:
                            result = await _rest_call_with_model(m_name, temp_try, max_tok_try)
                    else:
                        result = await _rest_call_with_model(m_name, temp_try, max_tok_try)

                    if result.get("success") and (result.get("content") or "").strip():
                        return result

                status = int(result.get("status") or 0)
                body_err = result.get("error", "")
                if status == 429 or ("RESOURCE_EXHAUSTED" in body_err):
                    # Respect Retry-After when present
                    retry_after = result.get("retry_after")
                    if retry_after:
                        try:
                            delay = float(retry_after)
                        except ValueError:
                            delay = 2.0
                    else:
                        delay = (self.backoff_base ** (attempt - 1)) + random.uniform(0.3, 1.2)
                    logger.warning("Gemini rate limit hit (attempt %s/%s). Backing off for %.2fs", attempt, attempts, delay)
                    await asyncio.sleep(delay)
                    continue
                if status in (500, 502, 503, 504):
                    delay = (self.backoff_base ** (attempt - 1)) + random.uniform(0.2, 0.8)
                    logger.warning("Gemini transient error %s (attempt %s/%s). Backing off for %.2fs", status, attempt, attempts, delay)
                    await asyncio.sleep(delay)
                    continue
                # Non-retryable
                break

            # After retries, fall back to SDK once
            try:
                # Recreate SDK model with overrides to apply temperature/tokens
                local_model = genai.GenerativeModel(
                    model_name=(model_candidates[-1][0] or model_name),
                    generation_config={
                        "temperature": model_candidates[-1][1],
                        "response_mime_type": "application/json",
                        "max_output_tokens": model_candidates[-1][2],
                    },
                )
                if _SEMAPHORE is not None:
                    async with _SEMAPHORE:
                        result = local_model.generate_content(prompt)
                else:
                    result = local_model.generate_content(prompt)
                content_text = getattr(result, "text", None)
                if not content_text and hasattr(result, "candidates"):
                    candidates = getattr(result, "candidates", [])
                    if candidates:
                        candidate0 = candidates[0]
                        content_obj = getattr(candidate0, "content", None)
                        parts = getattr(content_obj, "parts", None) if content_obj else None
                        if parts:
                            content_text = "".join(getattr(p, "text", "") for p in parts)
                if content_text and content_text.strip():
                    return {"success": True, "content": content_text}
            except Exception as sync_err:
                logger.error(f"Gemini SDK path error: {sync_err}")

            return {"success": False, "error": "Empty response from Gemini"}
        except Exception as e:
            logger.error(f"Error generating content with Gemini: {e}")
            return {"success": False, "error": str(e)} 