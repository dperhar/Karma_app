import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

from app.core.dependencies import container
from app.models.ai_profile import AnalysisStatus
from app.models.draft_comment import DraftStatus
from app.models.telegram_message import TelegramMessengerMessage
from app.repositories.ai_profile_repository import AIProfileRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.draft_comment_repository import DraftCommentRepository
from app.repositories.message_repository import \
    MessageRepository as TelegramMessageRepository
from app.repositories.negative_feedback_repository import \
    NegativeFeedbackRepository
from app.repositories.user_repository import UserRepository
from app.schemas.draft_comment import DraftCommentCreate, DraftCommentResponse
from app.services.domain.websocket_service import WebSocketService
from app.services.gemini_service import GeminiService
from app.services.telegram_service import TelegramService
from app.tasks.worker import celery_app
import requests

logger = logging.getLogger(__name__)


def _build_default_vibe_profile(lang: str = "en") -> Dict[str, Any]:
    """Construct a minimal but useful default vibe profile for development.

    Args:
        lang: Preferred language code ("ru" or "en").

    Returns:
        Dict[str, Any]: Default profile content localized.
    """
    if lang == "ru":
        return {
            "tone": "неформальный, по делу, немного остроумный",
            "verbosity": "средняя",
            "emoji_usage": "немного",
            "signature_phrases": [{"text": "погнали", "count": 3}],
            "ngrams": {"bigrams": ["давай сделаем", "выглядит круто"], "trigrams": ["это выглядит круто"]},
            "topics_of_interest": ["стартапы", "ИИ", "фаундерство", "рост"],
            "topic_weights": {"ИИ": 0.9, "стартапы": 0.85},
            "phrase_weights": {"погнали": 0.7},
            "style_markers": {
                "emoji_ratio": 0.01,
                "caps_ratio": 0.02,
                "avg_sentence_len_words": 9.5,
                "sentence_types": {"question": 0.15, "exclamation": 0.05, "declarative": 0.8},
                "punctuation": {
                    "exclamation_total": 1,
                    "question_total": 2,
                    "ellipsis_total": 0,
                    "dash_total": 0,
                    "hyphen_total": 1,
                    "quotes_angled_total": 0,
                    "quotes_straight_total": 0,
                    "parentheses_total": 0,
                },
                "language_distribution": {"ru_cyrillic": 1.0, "en_latin": 0.0},
                "fillers": {},
                "abbreviations": {"имхо": 1},
            },
            "digital_comm": {
                "greetings": ["йо", "привет"],
                "farewells": ["cheers"],
                "addressing_style": "ты",
                "typical_endings": ["."]
            },
            "signature_templates": [
                "Мысль: {{point}}. Что думаешь?",
                "Согласен по {{topic}} — я бы попробовал так: {{idea}}",
            ],
            "style_prompt": "Пиши кратко, по‑фаундерски, с лёгкой иронией и минимумом эмодзи.",
            "do_list": ["быть конкретным", "держаться темы"],
            "dont_list": ["пересказывать очевидное", "водить воду"],
        }

    # default EN
    return {
        "tone": "casual, concise, a bit witty",
        "verbosity": "medium",
        "emoji_usage": "light",
        "signature_phrases": [{"text": "let's go", "count": 3}],
        "ngrams": {"bigrams": ["let's go", "looks great"], "trigrams": ["this looks great"]},
        "topics_of_interest": ["startups", "ai", "founders", "growth"],
        "topic_weights": {"ai": 0.9, "startups": 0.85},
        "phrase_weights": {"let's go": 0.7},
        "style_markers": {
            "emoji_ratio": 0.01,
            "caps_ratio": 0.02,
            "avg_sentence_len_words": 9.5,
            "sentence_types": {"question": 0.15, "exclamation": 0.05, "declarative": 0.8},
            "punctuation": {
                "exclamation_total": 1,
                "question_total": 2,
                "ellipsis_total": 0,
                "dash_total": 0,
                "hyphen_total": 1,
                "quotes_angled_total": 0,
                "quotes_straight_total": 0,
                "parentheses_total": 0,
            },
            "language_distribution": {"ru_cyrillic": 0.0, "en_latin": 1.0},
            "fillers": {},
            "abbreviations": {"imo": 1},
        },
        "digital_comm": {
            "greetings": ["yo", "hey"],
            "farewells": ["cheers"],
            "addressing_style": "you",
            "typical_endings": ["."]
        },
        "signature_templates": [
            "Hot take: {{point}}. Curious what you think.",
            "Agree on {{topic}} – here's the angle I'd try: {{idea}}",
        ],
        "style_prompt": "Write concise, founder-like replies with light wit and minimal emoji.",
        "do_list": ["be concrete", "stay on-topic"],
        "dont_list": ["over-explain", "generic fluff"],
    }


@celery_app.task(name="tasks.fetch_telegram_chats_task", queue="drafts")
def fetch_telegram_chats_task(user_id: str, limit: int = 50, offset: int = 0):
    """
    Celery task to fetch user's Telegram chats.
    
    Following Principle 2: The Worker is the Intelligent, Stateful Engine.
    All Telegram API interactions must happen here in the Celery worker.
    """
    logger.info(f"Starting fetch chats task for user_id: {user_id}, limit: {limit}, offset: {offset}")
    asyncio.run(async_fetch_telegram_chats(user_id, limit, offset))


async def async_fetch_telegram_chats(user_id: str, limit: int, offset: int):
    """
    Async implementation of fetching Telegram chats.
    
    This task is self-contained and instantiates its own dependencies.
    """
    # GOOD: Task instantiates its own dependencies
    telegram_service = container.resolve(TelegramService)
    chat_repo = container.resolve(ChatRepository)
    websocket_service = container.resolve(WebSocketService)
    
    client = None
    try:
        # GOOD: All Telegram API interactions happen in the Celery worker
        client = await telegram_service.get_client(user_id)
        if not client:
            await websocket_service.send_user_notification(
                user_id, "chats_fetch_failed", {"error": "Failed to create Telegram client"}
            )
            return
            
        # Fetch chats from Telegram
        chats = await telegram_service.get_user_chats(user_id, limit=limit, offset=offset)
        
        # Store chats in database
        if chats:
            # Convert chat dictionaries to TelegramMessengerChat objects
            from app.models.chat import TelegramMessengerChat, TelegramMessengerChatType
            
            chat_objects = []
            for chat_data in chats:
                # Map the chat type string to enum
                chat_type_str = chat_data.get("type", "private")
                if chat_type_str == "channel":
                    chat_type = TelegramMessengerChatType.CHANNEL
                elif chat_type_str == "supergroup":
                    chat_type = TelegramMessengerChatType.SUPERGROUP
                elif chat_type_str == "group":
                    chat_type = TelegramMessengerChatType.GROUP
                else:
                    chat_type = TelegramMessengerChatType.PRIVATE
                
                chat_obj = TelegramMessengerChat(
                    telegram_id=chat_data.get("telegram_id"),
                    user_id=user_id,
                    type=chat_type,
                    title=chat_data.get("title"),
                    member_count=chat_data.get("member_count"),
                    comments_enabled=bool(chat_data.get("comments_enabled", False)),
                )
                chat_objects.append(chat_obj)
            
            # Save all chats at once
            saved_chats = await chat_repo.create_or_update_chats(chat_objects)
            logger.info(f"Successfully saved {len(saved_chats)} chats to database for user {user_id}")
        else:
            logger.warning(f"No chats found for user {user_id}")
        
        # Notify frontend via WebSocket
        await websocket_service.send_user_notification(
            user_id, 
            "chats_fetch_completed", 
            {
                "chats_count": len(chats),
                "limit": limit,
                "offset": offset
            }
        )
        
        logger.info(f"Successfully fetched {len(chats)} chats for user {user_id}")
        
    except Exception as e:
        logger.error(f"Chat fetch for user {user_id} failed: {e}", exc_info=True)
        await websocket_service.send_user_notification(
            user_id, "chats_fetch_failed", {"error": str(e)}
        )
    finally:
        if client:
            await telegram_service.disconnect_client(user_id)


@celery_app.task(name="tasks.analyze_vibe_profile", queue="analysis")
def analyze_vibe_profile(user_id: str, messages_limit: int = 200):
    """Celery task to analyze a user's vibe profile asynchronously.

    Args:
        user_id: The ID of the user whose profile to analyze
        messages_limit: Maximum number of latest sent messages to analyze
    """
    logger.info(f"Starting vibe profile analysis task for user_id: {user_id} with limit {messages_limit}")
    asyncio.run(async_analyze_vibe_profile(user_id, messages_limit))


async def async_analyze_vibe_profile(user_id: str, messages_limit: int = 200):
    """The async implementation of the vibe profile analysis."""
    # Resolve dependencies from the container
    telegram_service = container.resolve(TelegramService)
    gemini_service = container.resolve(GeminiService)
    ai_profile_repo = container.resolve(AIProfileRepository)
    websocket_service = container.resolve(WebSocketService)

    # Helper to send stage updates
    async def notify(stage: str, **extra: Any) -> None:
        payload: Dict[str, Any] = {"stage": stage}
        payload.update(extra)
        await websocket_service.send_user_notification(user_id, "vibe_profile_status", payload)

    await websocket_service.send_user_notification(user_id, "vibe_profile_analyzing", {})
    await notify("start", limit=messages_limit)

    client = None
    try:
        # Get user's telegram client
        await notify("tg_connecting")
        client = await telegram_service.get_client(user_id)
        if not client:
            await notify("tg_connect_failed")
            raise Exception("Failed to create Telegram client.")
        await notify("tg_connected")

        # Fetch user's sent messages
        await notify("fetch_start", per_dialog_limit_hint=100, dialogs_hint=50)
        user_sent_messages = await telegram_service.get_user_sent_messages(
            user_id, limit=messages_limit
        )
        fetched = len(user_sent_messages or [])
        await notify("fetch_done", messages_count=fetched)
        if not user_sent_messages or fetched < 20:
            await notify("insufficient_data", messages_count=fetched)
            raise Exception("Insufficient data for analysis.")

        # Use LLM to generate the vibe profile – with deterministic pre-computed stats
        message_texts = [msg.get("text", "") for msg in user_sent_messages if msg.get("text")]

        # Pre-compute stylistic stats to bias the model toward true copycat output
        from collections import Counter
        import itertools
        try:
            import regex as re2  # better unicode handling for emoji if available
            emoji_regex = re2.compile(r"\p{Emoji}")
        except Exception:  # pragma: no cover
            import re as re2
            emoji_regex = re2.compile(r"[\U0001F300-\U0001FAFF]")

        def normalize_text(text: str) -> str:
            return re.sub(r"\s+", " ", text.strip())

        cleaned = [normalize_text(t) for t in message_texts if isinstance(t, str) and t.strip()]
        tokens_lists = [t.lower().split() for t in cleaned]
        unigram_counter: Counter[str] = Counter(itertools.chain.from_iterable(tokens_lists))
        bigram_counter: Counter[tuple[str, str]] = Counter(
            itertools.chain.from_iterable(zip(lst, lst[1:]) for lst in tokens_lists if len(lst) > 1)
        )
        trigram_counter: Counter[tuple[str, str, str]] = Counter(
            itertools.chain.from_iterable(zip(lst, lst[1:], lst[2:]) for lst in tokens_lists if len(lst) > 2)
        )

        # Emoji ratio and punctuation habits
        total_chars = sum(len(t) for t in cleaned) or 1
        emoji_count = 0
        try:
            emoji_count = sum(len(emoji_regex.findall(t)) for t in cleaned)
        except Exception:
            pass
        emoji_ratio = round(emoji_count / total_chars, 4)
        exclam = sum(t.count("!") for t in cleaned)
        quest = sum(t.count("?") for t in cleaned)
        dots3 = sum(t.count("...") for t in cleaned)
        dashes = sum(t.count("—") for t in cleaned)
        hyphens = sum(t.count("-") for t in cleaned)
        quotes_angled = sum(t.count("«") + t.count("»") for t in cleaned)
        quotes_straight = sum(t.count('"') for t in cleaned)
        parens = sum(t.count("(") + t.count(")") for t in cleaned)
        endings = Counter((t.strip()[-1] if t.strip() else " ") for t in cleaned)

        # Sentence-level stats
        import re as _re
        sentences = list(
            itertools.chain.from_iterable(
                _re.split(r"(?<=[\.!?])\s+", t) for t in cleaned
            )
        )
        sentences = [s for s in sentences if s and any(ch.isalpha() for ch in s)]
        avg_sentence_len_words = round(
            sum(len(s.split()) for s in sentences) / max(len(sentences), 1), 2
        )
        sentence_types = {
            "question": round(sum(1 for s in sentences if s.strip().endswith("?")) / max(len(sentences), 1), 3),
            "exclamation": round(sum(1 for s in sentences if s.strip().endswith("!")) / max(len(sentences), 1), 3),
            "declarative": round(sum(1 for s in sentences if s.strip().endswith(".")) / max(len(sentences), 1), 3),
        }

        # Casing / CAPS
        uppercase_tokens = sum(1 for lst in tokens_lists for tok in lst if tok.isupper() and len(tok) > 1)
        total_tokens = sum(len(lst) for lst in tokens_lists) or 1
        caps_ratio = round(uppercase_tokens / total_tokens, 4)

        # Cyrillic vs Latin heuristic for language distribution
        def char_class_counts(text: str):
            cyr = sum(1 for ch in text if "\u0400" <= ch <= "\u04FF")
            lat = sum(1 for ch in text if ("a" <= ch.lower() <= "z"))
            return cyr, lat

        cyr_total, lat_total = 0, 0
        for t in cleaned:
            c, l = char_class_counts(t)
            cyr_total += c
            lat_total += l
        total_alpha = cyr_total + lat_total or 1
        lang_dist = {
            "ru_cyrillic": round(cyr_total / total_alpha, 3),
            "en_latin": round(lat_total / total_alpha, 3),
        }

        # Filler words and common abbreviations (RU/EN mix) – counts
        filler_words = [
            "типа", "как бы", "короче", "собственно", "вроде", "ну", "ээ", "мда",
        ]
        abbreviations = [
            "имхо", "лол", "кек", "спс", "пжл", "нзчт", "btw", "imo", "lol", "omg", "thx",
        ]
        fillers_count = {w: unigram_counter.get(w, 0) for w in filler_words}
        abbr_count = {w: unigram_counter.get(w, 0) for w in abbreviations}

        # Hapax legomena (unique tokens) – sample of most informative
        hapax = [w for w, c in unigram_counter.items() if c == 1][:100]

        precomputed_stats = {
            "top_unigrams": [w for w, _ in unigram_counter.most_common(50)],
            "top_bigrams": [" ".join(b) for b, _ in bigram_counter.most_common(30)],
            "top_trigrams": [" ".join(t) for t, _ in trigram_counter.most_common(20)],
            "emoji_ratio": emoji_ratio,
            "punctuation": {
                "exclamation_total": exclam,
                "question_total": quest,
                "ellipsis_total": dots3,
                "dash_total": dashes,
                "hyphen_total": hyphens,
                "quotes_angled_total": quotes_angled,
                "quotes_straight_total": quotes_straight,
                "parentheses_total": parens,
                "endings_distribution": dict(endings),
            },
            "language_distribution": lang_dist,
            "avg_msg_len_chars": round(sum(len(t) for t in cleaned) / max(len(cleaned), 1), 2),
            "avg_sentence_len_words": avg_sentence_len_words,
            "sentence_types": sentence_types,
            "caps_ratio": caps_ratio,
            "fillers": fillers_count,
            "abbreviations": abbr_count,
            "hapax_sample": hapax,
        }

        # Sample representative messages for style (cap for prompt size)
        sample_count = min(400, len(cleaned))
        sample_stride = max(1, len(cleaned) // max(sample_count, 1))
        sample_messages = cleaned[::sample_stride][:sample_count]
        sample_blob = "\n".join(sample_messages)
        max_chars = 25000
        if len(sample_blob) > max_chars:
            sample_blob = sample_blob[:max_chars]

        await notify("llm_prepare", prompt_chars=len(sample_blob))

        prompt = f"""
        You are an uncompromising style mimic. Build a copycat persona strictly from the user's own messages.
        Return ONLY valid JSON (no code fences). Schema:
        {{
          "tone": string,
          "verbosity": string,
          "emoji_usage": string,
          "signature_phrases": [{{"text": string, "count": int}}],
          "ngrams": {{"bigrams": string[], "trigrams": string[]}},
          "topics_of_interest": string[],
          "topic_weights": {{string: number}},
          "phrase_weights": {{string: number}},
          "style_markers": {{
            "emoji_ratio": float,
            "caps_ratio": float,
            "avg_sentence_len_words": float,
            "sentence_types": {{"question": float, "exclamation": float, "declarative": float}},
            "punctuation": {{
              "exclamation_total": int,
              "question_total": int,
              "ellipsis_total": int,
              "dash_total": int,
              "hyphen_total": int,
              "quotes_angled_total": int,
              "quotes_straight_total": int,
              "parentheses_total": int
            }},
            "language_distribution": {{"ru_cyrillic": float, "en_latin": float}},
            "fillers": {{string: int}},
            "abbreviations": {{string: int}}
          }},
          "digital_comm": {{
            "greetings": string[],
            "farewells": string[],
            "addressing_style": string,   // e.g., ты/Вы/nicknames/no address
            "typical_endings": string[]   // e.g., no punctuation, emoji endings, ellipsis
          }},
          "signature_templates": string[],
          "style_prompt": string,
          "do_list": string[],
          "dont_list": string[]
        }}

        RULES:
        - Ground all claims in PRECOMPUTED_STATS and SAMPLE_MESSAGES. Do not invent.
        - LANGUAGE: If PRECOMPUTED_STATS.language_distribution.ru_cyrillic > 0.5, write ALL FIELDS IN RUSSIAN; else in ENGLISH.
        - signature_phrases should come from recurring tokens/phrases; include counts.
        - Keep arrays ≤ 12 items. Prefer exact phrases from messages when possible.

        PRECOMPUTED_STATS:
        {json.dumps(precomputed_stats, ensure_ascii=False)}

        SAMPLE_MESSAGES_START
        {sample_blob}
        SAMPLE_MESSAGES_END
        """
        await notify("llm_start", model="gemini-2.5-pro")
        # Allow per-user overrides from temporary ai settings via websocket/UI
        ai_overrides: Dict[str, Any] = {}
        try:
            # Pull lightweight overrides from ai_profile.vibe_profile_json if present under key 'gen_overrides'
            gen_overrides = getattr(ai_profile, "vibe_profile_json", {}) or {}
            if isinstance(gen_overrides, dict):
                o = gen_overrides.get("gen_overrides") or {}
                if isinstance(o, dict):
                    ai_overrides = {
                        k: v
                        for k, v in o.items()
                        if k in {"model", "temperature", "max_output_tokens"}
                    }
        except Exception:
            ai_overrides = {}

        response = await gemini_service.generate_content(prompt, overrides=ai_overrides)
        if not response or not response.get("success"):
            from app.core.config import settings
            err_msg = (response or {}).get("error", "LLM analysis failed.")
            logger.error(f"LLM analysis failed for user {user_id}: {err_msg}")
            await websocket_service.send_user_notification(user_id, "vibe_profile_failed", {"error": err_msg})
            await notify("llm_failed", error=err_msg)
            if settings.IS_DEVELOP:
                await notify("dev_seed_start")
                # Choose default profile language based on recent messages
                try:
                    dom_lang = "ru" if precomputed_stats.get("language_distribution", {}).get("ru_cyrillic", 0) > 0.5 else "en"
                except Exception:
                    dom_lang = "en"
                default_profile = _build_default_vibe_profile(dom_lang)
                ai_profile = await ai_profile_repo.get_ai_profile_by_user(user_id)
                if not ai_profile:
                    ai_profile = await ai_profile_repo.create_ai_profile(user_id=user_id)
                await ai_profile_repo.mark_analysis_completed(
                    profile_id=ai_profile.id,
                    vibe_profile=default_profile,
                    messages_count=0,
                )
                await websocket_service.send_user_notification(user_id, "vibe_profile_completed", {"profile": default_profile})
                await notify("dev_seed_done")
            return

        content = response.get("content", "").strip()
        await notify("llm_response_received", content_preview=content[:120])
        json_match = re.search(r"\{[\s\S]*\}", content)
        if not json_match:
            msg = "LLM did not return a valid JSON object."
            logger.error(f"{msg} for user {user_id}: {content[:200]}")
            await websocket_service.send_user_notification(
                user_id, "vibe_profile_failed", {"error": msg}
            )
            await notify("llm_parse_failed")
            return

        vibe_profile = json.loads(json_match.group(0))
        try:
            dom_lang = "ru" if precomputed_stats.get("language_distribution", {}).get("ru_cyrillic", 0) > 0.5 else "en"
            vibe_profile["dominant_language"] = dom_lang
        except Exception:
            pass
        await notify("llm_parsed_ok")

        # Save the profile
        await notify("persist_start")
        ai_profile = await ai_profile_repo.get_ai_profile_by_user(user_id)
        if not ai_profile:
            ai_profile = await ai_profile_repo.create_ai_profile(user_id=user_id)

        await ai_profile_repo.mark_analysis_completed(
            profile_id=ai_profile.id,
            vibe_profile=vibe_profile,
            messages_count=len(user_sent_messages),
        )
        await notify("persist_done")

        await websocket_service.send_user_notification(
            user_id, "vibe_profile_completed", {"profile": vibe_profile}
        )
        await notify("done")
        logger.info(f"Successfully completed vibe profile analysis for user {user_id}.")

        # Kick off immediate draft generation for recent channel posts so the feed is not empty
        try:
            generate_drafts_for_user_recent_posts.delay(user_id=user_id)
            logger.info(
                "Queued generate_drafts_for_user_recent_posts for user %s right after analysis",
                user_id,
            )
        except Exception as _e:
            logger.error(f"Failed to queue initial drafts generation for user {user_id}: {_e}")

    except Exception as e:
        logger.error(f"Vibe profile analysis for user {user_id} failed: {e}", exc_info=True)
        await websocket_service.send_user_notification(
            user_id, "vibe_profile_failed", {"error": str(e)}
        )
        await notify("failed", error=str(e))
    finally:
        if client:
            await notify("tg_disconnect")
            await telegram_service.disconnect_client(user_id)


@celery_app.task(name="tasks.seed_ai_profile_dev", queue="analysis")
def seed_ai_profile_dev(user_id: str):
    """Dev-only helper to mark AI profile as completed with a reasonable default.

    Used when running locally without a Telegram session so the UI can function.
    """
    asyncio.run(async_seed_ai_profile_dev(user_id))


async def async_seed_ai_profile_dev(user_id: str):
    from app.repositories.ai_profile_repository import AIProfileRepository
    websocket_service = container.resolve(WebSocketService)
    ai_profile_repo = container.resolve(AIProfileRepository)

    ai_profile = await ai_profile_repo.get_ai_profile_by_user(user_id)
    if not ai_profile:
        ai_profile = await ai_profile_repo.create_ai_profile(user_id=user_id)

    # Minimal but useful vibe profile so UI can render
    default_profile: Dict[str, Any] = {
        "tone": "casual, concise, a bit witty",
        "verbosity": "medium",
        "emoji_usage": "light",
        "signature_phrases": [{"text": "let's go", "count": 3}],
        "ngrams": {"bigrams": ["let's go", "looks great"], "trigrams": ["this looks great"]},
        "topics_of_interest": ["startups", "ai", "founders", "growth"],
        "topic_weights": {"ai": 0.9, "startups": 0.85},
        "phrase_weights": {"let's go": 0.7},
        "style_markers": {
            "emoji_ratio": 0.01,
            "caps_ratio": 0.02,
            "avg_sentence_len_words": 9.5,
            "sentence_types": {"question": 0.15, "exclamation": 0.05, "declarative": 0.8},
            "punctuation": {
                "exclamation_total": 1,
                "question_total": 2,
                "ellipsis_total": 0,
                "dash_total": 0,
                "hyphen_total": 1,
                "quotes_angled_total": 0,
                "quotes_straight_total": 0,
                "parentheses_total": 0,
            },
            "language_distribution": {"ru_cyrillic": 0.0, "en_latin": 1.0},
            "fillers": {},
            "abbreviations": {"imo": 1},
        },
        "digital_comm": {
            "greetings": ["yo", "hey"],
            "farewells": ["cheers"],
            "addressing_style": "you",
            "typical_endings": ["."]
        },
        "signature_templates": [
            "Hot take: {{point}}. Curious what you think.",
            "Agree on {{topic}} – here's the angle I'd try: {{idea}}",
        ],
        "style_prompt": "Write concise, founder-like replies with light wit and minimal emoji.",
        "do_list": ["be concrete", "stay on-topic"],
        "dont_list": ["over-explain", "generic fluff"],
    }

    await ai_profile_repo.mark_analysis_completed(
        profile_id=ai_profile.id,
        vibe_profile=default_profile,
        messages_count=0,
    )

    try:
        await websocket_service.send_user_notification(
            user_id, "vibe_profile_completed", {"profile": default_profile}
        )
    except Exception:
        pass

@celery_app.task(name="tasks.generate_draft_for_post")
def generate_draft_for_post(
    user_id: str,
    post_data: Dict[str, Any],
    rejected_draft_id: Optional[str] = None,
    rejection_reason: Optional[str] = None,
):
    """Celery task to generate a draft comment for a post."""
    logger.info(f"Starting draft generation task for user_id: {user_id}")
    asyncio.run(
        async_generate_draft_for_post(
            user_id, post_data, rejected_draft_id, rejection_reason
        )
    )


@celery_app.task(name="tasks.seed_dev_drafts_from_feed", queue="drafts")
def seed_dev_drafts_from_feed(user_id: str, limit: int = 6):
    """DEV: Seed initial drafts using the public feed when Telegram session is absent.

    Pulls posts from the API feed and creates lightweight drafts so the UI is populated.
    """
    asyncio.run(async_seed_dev_drafts_from_feed(user_id, limit))


async def async_seed_dev_drafts_from_feed(user_id: str, limit: int = 6):
    from app.core.config import settings
    draft_repo = container.resolve(DraftCommentRepository)
    user_repo = container.resolve(UserRepository)
    websocket_service = container.resolve(WebSocketService)

    try:
        # Fetch feed posts from API inside container
        base = f"http://localhost:8000{settings.API_V1_STR}"
        resp = requests.get(f"{base}/feed", params={"page": 1, "limit": limit}, timeout=5)
        posts = (resp.json().get("data") or {}).get("posts") or []
    except Exception:
        posts = []

    if not posts:
        return

    user = await user_repo.get_user(user_id)
    lang = "ru"
    try:
        vp = getattr(user, "ai_profile", None).vibe_profile_json if getattr(user, "ai_profile", None) else {}
        dom = (vp or {}).get("dominant_language")
        if dom in ("ru", "en"):
            lang = dom
    except Exception:
        pass

    for idx, p in enumerate(posts):
        try:
            text = p.get("text") or ""
            if not text:
                continue
            draft_text = (
                f"Согласен. Интересная мысль. 🚀" if lang == "ru" else "Interesting take. I like it. 🚀"
            )
            gen_params: Dict[str, Any] = {}
            ch = p.get("channel") or {}
            if ch.get("title"):
                gen_params["channel_title"] = ch.get("title")
            if p.get("channel_telegram_id"):
                gen_params["channel_telegram_id"] = int(p["channel_telegram_id"])  # type: ignore[arg-type]

            create = DraftCommentCreate(
                original_message_id=f"dev-seed-{idx}",
                user_id=user_id,
                persona_name=getattr(getattr(user, "ai_profile", None), "persona_name", None),
                ai_model_used=str(getattr(getattr(user, "preferred_ai_model", None), "value", "gemini-pro")),
                original_post_text_preview=text[:500],
                original_post_content=text,
                original_post_url=p.get("url"),
                draft_text=draft_text,
                generation_params=gen_params or None,
            )
            new_draft = await draft_repo.create_draft_comment(**create.model_dump())
            if new_draft:
                await websocket_service.send_user_notification(
                    user_id, "new_ai_draft", {"draft": DraftCommentResponse.model_validate(new_draft).model_dump(mode="json")}
                )
        except Exception:
            continue

async def async_generate_draft_for_post(
    user_id: str,
    post_data: Dict[str, Any],
    rejected_draft_id: Optional[str] = None,
    rejection_reason: Optional[str] = None,
):
    """The async implementation of draft generation."""
    # Resolve dependencies
    user_repo = container.resolve(UserRepository)
    ai_profile_repo = container.resolve(AIProfileRepository)
    draft_repo = container.resolve(DraftCommentRepository)
    feedback_repo = container.resolve(NegativeFeedbackRepository)
    gemini_service = container.resolve(GeminiService)
    chat_repo = container.resolve(ChatRepository)
    message_repo = container.resolve(TelegramMessageRepository)
    websocket_service = container.resolve(WebSocketService)

    try:
        user = await user_repo.get_user(user_id)
        ai_profile = await ai_profile_repo.get_ai_profile_by_user(user_id)
        if not user or not ai_profile or not getattr(ai_profile, "vibe_profile_json", None):
            raise Exception("User AI profile not found or incomplete.")

        # Handle regeneration case
        if rejected_draft_id:
            rejected_draft = await draft_repo.get_draft_comment(rejected_draft_id)
            if rejected_draft:
                await feedback_repo.create_negative_feedback(
                    user_id=user_id,
                    rejected_comment_text=rejected_draft.draft_text,
                    original_post_content=rejected_draft.original_post_content,
                    original_post_url=rejected_draft.original_post_url,
                    rejection_reason=rejection_reason,
                    ai_model_used=rejected_draft.ai_model_used,
                    draft_comment_id=rejected_draft_id,
                )
                await draft_repo.update_draft_comment(
                    rejected_draft_id, status=DraftStatus.REJECTED
                )

        # Check post relevance (allow forced generation for initial seeding)
        force_generate: bool = bool(post_data.get("force_generate", False))
        vibe_profile = ai_profile.vibe_profile_json
        topics_of_interest = vibe_profile.get("topics_of_interest", [])
        post_text = post_data.get("original_post_content", "").lower()
        is_relevant = any(topic.lower() in post_text for topic in topics_of_interest)
        if not topics_of_interest:
            is_relevant = True

        if not (is_relevant or force_generate):
            logger.info(
                f"Post not relevant for user {user_id}. Skipping draft generation."
            )
            return

        # Construct prompt
        negative_feedback = await feedback_repo.get_negative_feedback_by_user(
            user_id, limit=10
        )
        feedback_context = "\n".join(
            [
                f"- REJECTED: '{fb.rejected_comment_text}' because '{fb.rejection_reason}'"
                for fb in negative_feedback
            ]
        )

        # Build optional channel context from recent messages in the same channel, if available
        channel_context = ""
        channel_telegram_id = post_data.get("channel_telegram_id")
        if channel_telegram_id:
            db_chat = await chat_repo.get_chat_by_telegram_id(int(channel_telegram_id), user_id)
            if db_chat:
                # Attempt to load saved per-channel context from the user's latest draft in this chat
                try:
                    saved_ctx = await draft_repo.get_latest_context_for_chat(user_id=user_id, chat_db_id=db_chat.id)
                except Exception:
                    saved_ctx = None

                recent_msgs = await message_repo.get_chat_messages(db_chat.id, limit=5, offset=0)
                if recent_msgs:
                    channel_context_lines = [
                        f"- {getattr(m, 'text', '')[:160]}" for m in recent_msgs if getattr(m, 'text', '')
                    ]
                    channel_context = "\n".join(channel_context_lines)
                # Prepend/merge any saved channel/topic context authored by the user
                if saved_ctx and isinstance(saved_ctx, dict) and saved_ctx.get("channel_context"):
                    channel_context = f"[USER_TOPIC_CONTEXT]\n{saved_ctx.get('channel_context')}\n\n[RECENT_CHANNEL_ACTIVITY]\n{channel_context}"

        # Pull user's recently POSTED drafts as positive examples to imitate
        try:
            recent_posted = await draft_repo.get_recent_posted_by_user(user_id=user_id, limit=8)
            examples_weighted: list[str] = []
            now_ts = __import__('time').time()
            for p in recent_posted:
                text = (getattr(p, 'final_text_to_post', None) or getattr(p, 'edited_text', None) or p.draft_text or '').strip()
                if not text:
                    continue
                # Recency weight: newer -> closer to 1.0
                updated_ts = getattr(p, 'updated_at', None).timestamp() if getattr(p, 'updated_at', None) else now_ts
                age_hours = max((now_ts - updated_ts) / 3600.0, 0.0)
                recency_w = max(0.3, 1.0 / (1.0 + age_hours / 24.0))  # >= 0.3
                # User-curated boost if marked as style example
                gp = getattr(p, 'generation_params', None) or {}
                curated_boost = 0.2 if isinstance(gp, dict) and gp.get('is_style_example') else 0.0
                # Baseline boost for anything the user actually sent
                posted_boost = 0.1
                weight = min(1.0, recency_w + posted_boost + curated_boost)
                examples_weighted.append(f"- [WEIGHT {weight:.2f}] {text}")
            positive_examples = "\n".join(examples_weighted)
        except Exception:
            positive_examples = ""

        prompt = f"""
        You are an AI assistant generating a Telegram comment for a user.
        USER VIBE PROFILE: {json.dumps(ai_profile.vibe_profile_json, indent=2)}
        POST TO COMMENT ON: {post_data.get('original_post_content')}
        CHANNEL CONTEXT (recent messages):
        {channel_context}
        
        USER'S PAST REJECTIONS (learn from these mistakes):
        {feedback_context if feedback_context else "None"}

        USER'S PAST APPROVED/POSTED EXAMPLES (imitate this vibe):
        {positive_examples if positive_examples else "None"}

        INSTRUCTIONS:
        1. Generate a comment that perfectly matches the user's vibe (tone, verbosity, emoji usage).
        2. The comment must be relevant to the post.
        3. Avoid making comments similar to the rejected ones.
        4. Generate ONLY the comment text.
        5. If the post seems borderline off-topic, still produce a short, witty, on-topic reply or ask a clarifying question to stay relevant.
        """

        # Generate comment
        # Allow per-user overrides from temporary ai settings via websocket/UI
        ai_overrides: Dict[str, Any] = {}
        try:
            # Pull lightweight overrides from ai_profile.vibe_profile_json if present under key 'gen_overrides'
            gen_overrides = getattr(ai_profile, "vibe_profile_json", {}) or {}
            if isinstance(gen_overrides, dict):
                o = gen_overrides.get("gen_overrides") or {}
                if isinstance(o, dict):
                    ai_overrides = {
                        k: v
                        for k, v in o.items()
                        if k in {"model", "temperature", "max_output_tokens"}
                    }
        except Exception:
            ai_overrides = {}

        response = await gemini_service.generate_content(prompt, overrides=ai_overrides)
        if not response or not response.get("success"):
            # Graceful degrade: create minimal draft if rate-limited, so feed stays useful
            error_text = str(response.get("error", "unknown error")) if isinstance(response, dict) else "unknown"
            if "RESOURCE_EXHAUSTED" in error_text or "429" in error_text:
                draft_text = (
                    "Круто. Вижу тему, которая мне близка. Подписываюсь на апдейт. "
                    "(AI временно ограничен по квоте, поэтому коротко.)"
                )
            else:
                raise Exception("LLM comment generation failed.")
        else:
            draft_text = response.get("content", "").strip()

        # Save draft
        # Enrich generation params with channel title for UI/learning and real Telegram IDs
        gen_params: Dict[str, Any] = {}
        try:
            if channel_telegram_id and db_chat:
                gen_params["channel_title"] = getattr(db_chat, "title", None)
                gen_params["channel_telegram_id"] = int(channel_telegram_id)
            elif isinstance(post_data.get("channel"), dict):
                gen_params["channel_title"] = post_data.get("channel", {}).get("title")
                if post_data.get("channel", {}).get("id"):
                    gen_params["channel_telegram_id"] = int(post_data.get("channel", {}).get("id"))
            # Include original Telegram message id if available in payload
            if post_data.get("original_message_telegram_id") and str(post_data.get("original_message_telegram_id")).isdigit():
                gen_params["post_telegram_id"] = int(post_data.get("original_message_telegram_id"))
            else:
                # Try to resolve DB message id to Telegram id
                try:
                    db_msg_id = post_data.get("original_message_id")
                    if db_msg_id and str(db_msg_id).isdigit():
                        db_msg = await message_repo.get_message(str(db_msg_id))
                        tg_id = getattr(db_msg, "telegram_id", None) if db_msg else None
                        if tg_id:
                            gen_params["post_telegram_id"] = int(tg_id)
                except Exception:
                    pass
        except Exception:
            pass

        draft_create_data = DraftCommentCreate(
            original_message_id=post_data.get("original_message_id", "unknown"),
            user_id=user_id,
            persona_name=ai_profile.persona_name,
            ai_model_used=user.preferred_ai_model.value
            if user.preferred_ai_model
            else "gemini-pro",
            original_post_text_preview=post_data.get("original_post_content", "")[:500],
            original_post_content=post_data.get("original_post_content"),
            original_post_url=post_data.get("original_post_url"),
            draft_text=draft_text,
            generation_params=gen_params or None,
        )
        new_draft = await draft_repo.create_draft_comment(
            **draft_create_data.model_dump()
        )

        # Notify user
        try:
            draft_payload = DraftCommentResponse.model_validate(new_draft).model_dump(mode="json")
        except Exception:
            draft_payload = {
                "id": getattr(new_draft, "id", None),
                "user_id": user_id,
                "original_message_id": post_data.get("original_message_id"),
                "draft_text": draft_text,
                "status": str(getattr(new_draft, "status", DraftStatus.DRAFT)),
            }
        await websocket_service.send_user_notification(
            user_id, "new_ai_draft", {"draft": draft_payload}
        )
        logger.info(f"Successfully generated draft {new_draft.id} for user {user_id}.")

    except Exception as e:
        logger.error(f"Draft generation for user {user_id} failed: {e}", exc_info=True)
        await websocket_service.send_user_notification(
            user_id, "draft_generation_failed", {"error": str(e)}
        )


@celery_app.task(name="tasks.check_for_new_posts_and_generate_drafts", queue="scheduler")
def check_for_new_posts_and_generate_drafts():
    """Celery task to periodically check for new posts and generate drafts."""
    logger.info("Starting scheduled task: check_for_new_posts_and_generate_drafts")
    asyncio.run(async_check_for_new_posts())


async def async_check_for_new_posts():
    """The async implementation of the scheduled check."""
    user_repo = container.resolve(UserRepository)
    telegram_service = container.resolve(TelegramService)
    message_repo = container.resolve(TelegramMessageRepository)
    chat_repo = container.resolve(ChatRepository)

    active_users = await user_repo.get_users()
    for user in active_users:
        if not user.telegram_connection or not user.telegram_connection.is_session_valid():
            continue

        client = None
        try:
            client = await telegram_service.get_client(user.id)
            if not client:
                continue

            async for dialog in client.iter_dialogs(limit=20):
                if dialog.is_channel:
                    db_chat = await chat_repo.get_chat_by_telegram_id(dialog.id, user.id)
                    if not db_chat:
                        continue

                    async for message in client.iter_messages(dialog, limit=10):
                        # This is a simplified check. A real implementation would
                        # track last seen message IDs per channel.
                        db_messages = await message_repo.create_or_update_messages(
                            [
                                TelegramMessengerMessage(
                                    telegram_id=message.id,
                                    chat_id=db_chat.id,
                                    text=message.text,
                                    date=telegram_service._convert_to_naive_utc(message.date),
                                )
                            ]
                        )
                        db_message_id = db_messages[0].id

                        post_data = {
                            "original_message_id": db_message_id,
                            "original_post_content": message.text,
                            "original_post_url": f"https://t.me/{dialog.entity.username}/{message.id}"
                            if hasattr(dialog.entity, "username")
                            and dialog.entity.username
                            else None,
                        }
                        generate_draft_for_post.delay(user_id=user.id, post_data=post_data)
        except Exception as e:
            logger.error(f"Failed to process user {user.id} in scheduled task: {e}")
        finally:
            if client:
                await telegram_service.disconnect_client(user.id) 


@celery_app.task(name="tasks.generate_drafts_for_user_recent_posts", queue="drafts")
def generate_drafts_for_user_recent_posts(user_id: str, dialogs_limit: int = 20, per_dialog_messages: int = 5):
    """Generate initial drafts for a single user by scanning recent channel posts.

    This is invoked after vibe analysis completes to immediately populate the feed.
    """
    logger.info(
        "Starting generate_drafts_for_user_recent_posts for user_id=%s (dialogs_limit=%s, per_dialog_messages=%s)",
        user_id,
        dialogs_limit,
        per_dialog_messages,
    )
    asyncio.run(async_generate_drafts_for_user_recent_posts(user_id, dialogs_limit, per_dialog_messages))


async def async_generate_drafts_for_user_recent_posts(user_id: str, dialogs_limit: int = 20, per_dialog_messages: int = 5):
    """Async implementation to fetch recent channel posts for one user and queue draft generation."""
    user_repo = container.resolve(UserRepository)
    telegram_service = container.resolve(TelegramService)
    message_repo = container.resolve(TelegramMessageRepository)
    chat_repo = container.resolve(ChatRepository)

    user = await user_repo.get_user(user_id)
    if not user or not user.telegram_connection or not user.telegram_connection.is_session_valid():
        logger.info("User %s missing valid telegram connection; skipping initial drafts.", user_id)
        return

    client = None
    try:
        client = await telegram_service.get_client(user.id)
        if not client:
            return

        async for dialog in client.iter_dialogs(limit=dialogs_limit):
            if not dialog.is_channel:
                continue

            db_chat = await chat_repo.get_chat_by_telegram_id(dialog.id, user.id)
            if not db_chat:
                # Create chat record on the fly so drafts can be generated immediately
                from app.models.chat import TelegramMessengerChat, TelegramMessengerChatType
                created_list = await chat_repo.create_or_update_chats(
                    [
                        TelegramMessengerChat(
                            telegram_id=int(dialog.id),
                            user_id=user.id,
                            type=TelegramMessengerChatType.CHANNEL,
                            title=getattr(dialog.entity, "title", "Unnamed Channel"),
                            comments_enabled=True,
                        )
                    ]
                )
                db_chat = created_list[0] if created_list else None
                if not db_chat:
                    continue

            async for message in client.iter_messages(dialog, limit=per_dialog_messages):
                if not getattr(message, "text", None):
                    continue
                saved = await message_repo.create_or_update_messages(
                    [
                        TelegramMessengerMessage(
                            telegram_id=message.id,
                            chat_id=db_chat.id,
                            text=message.text,
                            date=telegram_service._convert_to_naive_utc(message.date),
                        )
                    ]
                )
                db_message_id = saved[0].id
                post_data = {
                    "original_message_id": db_message_id,
                    "original_post_content": message.text,
                    "original_post_url": (
                        f"https://t.me/{getattr(dialog.entity, 'username', None)}/{message.id}"
                        if getattr(dialog.entity, "username", None) else None
                    ),
                    "channel_telegram_id": int(dialog.id),
                    "force_generate": True,
                }
                generate_draft_for_post.delay(user_id=user.id, post_data=post_data)
    except Exception as e:
        logger.error("Failed generate_drafts_for_user_recent_posts for user %s: %s", user_id, e)
    finally:
        if client:
            await telegram_service.disconnect_client(user.id)