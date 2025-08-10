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
        self.api_key = raw_key.strip()
        self.rest_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
        # Rate limit/backoff config
        self.max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "4"))
        self.backoff_base = float(os.getenv("GEMINI_BACKOFF_BASE", "1.8"))
        self.min_delay_ms = int(os.getenv("GEMINI_MIN_DELAY_MS", "150"))
        self.jitter_ms = int(os.getenv("GEMINI_JITTER_MS", "200"))
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables. Using mock mode.")
            self.mock_mode = True
        else:
            try:
                logger.info(f"Gemini API key loaded (length={len(self.api_key)}). Initializing client...")
                genai.configure(api_key=self.api_key)
                # Library client kept as a fallback
                self.model = genai.GenerativeModel(
                    model_name='gemini-2.5-pro',
                    generation_config={
                        "temperature": 0.2,
                        "response_mime_type": "application/json",
                    },
                )
                self.chat = self.model.start_chat(history=[])
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

            # Resolve per-request overrides
            model_name = (overrides or {}).get("model") or "gemini-2.5-pro"
            try:
                temperature = float((overrides or {}).get("temperature", self.model.generation_config.get("temperature", 0.2)))
            except Exception:
                temperature = 0.2
            try:
                max_output_tokens = int((overrides or {}).get("max_output_tokens", 512))
            except Exception:
                max_output_tokens = 512

            # Small pre-call delay to shape burstiness
            try:
                pre_delay = (self.min_delay_ms + random.randint(0, self.jitter_ms)) / 1000.0
                if pre_delay > 0:
                    await asyncio.sleep(pre_delay)
            except Exception:
                pass

            # Prefer REST v1beta call for deterministic behavior with gemini-2.5-pro
            async def _rest_call() -> Dict[str, Any]:
                headers = {
                    "Content-Type": "application/json",
                    "X-goog-api-key": self.api_key,
                }
                body = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_output_tokens,
                    },
                }
                rest_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                resp = requests.post(rest_url, json=body, headers=headers, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    text_segments: list[str] = []
                    for cand in data.get("candidates", [])[:1]:
                        content = cand.get("content", {})
                        for part in content.get("parts", []):
                            t = part.get("text")
                            if t:
                                text_segments.append(t)
                    content_text = "".join(text_segments).strip()
                    if content_text:
                        return {"success": True, "content": content_text}
                    return {"success": False, "error": "Empty content"}
                # Handle rate limit and transient errors
                if resp.status_code in (429, 500, 502, 503, 504):
                    return {"success": False, "error": resp.text, "status": resp.status_code, "retry_after": resp.headers.get("retry-after")}
                # Other errors
                logger.error("Gemini REST error %s: %s", resp.status_code, resp.text[:500])
                return {"success": False, "error": resp.text, "status": resp.status_code}

            attempts = self.max_retries
            for attempt in range(1, attempts + 1):
                # Concurrency guard
                if _SEMAPHORE is not None:
                    async with _SEMAPHORE:
                        result = await _rest_call()
                else:
                    result = await _rest_call()

                if result.get("success"):
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
                    model_name=model_name,
                    generation_config={
                        "temperature": temperature,
                        "response_mime_type": "application/json",
                        "max_output_tokens": max_output_tokens,
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