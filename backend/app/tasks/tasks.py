import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

from app.core.dependencies import container
import random
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
from app.services.redis_service import RedisService
from app.services.langchain_service import LangChainService
from app.tasks.worker import celery_app
import requests
import time
import os

logger = logging.getLogger(__name__)


# Digital Twin default behavior config (can be overridden via ai_profile.vibe_profile_json['dt_config'])
DEFAULT_DT_CONFIG: Dict[str, Any] = {
    "persona": {
        "core_archetype": "SYSTEM_HEALER",
        "values": {
            "systemic_honesty": 1.0,
            "depth": 1.0,
            "sovereignty": 1.0,
            "vitality": 0.8
        },
        "talents": ["XRAY_VISION", "ALCHEMY", "SURGICAL_FORMULATION"],
        "voice": {
            "tone": "ruthless_empathetic",
            "provocation_level": 0.6,
            "vulnerability_level": 0.5,
            "lexicon": {
                "system": ["паттерн", "динамика", "структура", "конфликт"],
                "psychology": ["проекция", "тень", "изгнанник", "саботаж"],
                "direct": ["хуйня", "пиздец", "разъеб"],
                "banned_starters": []
            }
        }
    },
    "dynamic_filters": {
        "sub_personalities": {
            "INQUISITOR": {
                "triggers": ["булшит", "поверхност", "хайп", "манипуляц", "логическ", "данн", "метрик", "факт"],
                "semantic_hints": [
                    "логическая ошибка", "путаете причину и следствие", "эзотерика как избегание ответственности",
                    "ответственность за результат", "юнит-экономика", "покажите данные/доказательства"
                ],
                "examples": [
                    "'Доверять потоку' часто маскирует страх смотреть в цифры. Где данные?",
                    "Интересная метрика, но без X и Y это красивая фантазия"
                ],
                "style_mod": {"temperature": 0.35, "verbosity": "low"}
            },
            "HEALER": {
                "triggers": ["боль", "уязвим", "страх", "стыд", "вина", "отверж", "привязанн"],
                "semantic_hints": [
                    "внутренний ребенок", "IFS", "саморегуляция", "любящий взгляд", "ресурс", "самоподдержка",
                    "эмоциональная волна", "сострадание без инфантильности"
                ],
                "examples": [
                    "Похоже, первая реакция — гнев. Если подождать волну, там часто страх быть ненужным",
                    "Пока не спишете 'эмоциональный долг', любая новая система будет мертвому припарки"
                ],
                "style_mod": {"temperature": 0.45, "vulnerability": 0.7}
            },
            "ARCHITECT": {
                "triggers": ["хаос", "структур", "процесс", "метрик", "okr", "kpi", "найм", "операционк", "модель"],
                "semantic_hints": [
                    "структура", "процесс", "операционка", "OKR", "KPI", "юнит-экономика", "фундамент",
                    "связка целей и рутины"
                ],
                "examples": [
                    "Как вы убедились, что цели не противоречат ежедневной рутине?",
                    "Где связь между стратегией и операционкой?"
                ],
                "style_mod": {"temperature": 0.4, "structure": "clear_steps"}
            },
            "SHAMAN": {
                "triggers": ["энерг", "смысл", "кризис", "выгор", "смерт", "сексуал", "тень", "проекция", "магия"],
                "semantic_hints": [
                    "тень", "проекция", "смерть/возрождение", "ритуал", "алхимия", "символ", "втянуть энергию", "сжечь"
                ],
                "examples": [
                    "Твой бизнес не убивает тебя. Он показывает, где ты убиваешь себя",
                    "Мы уже прожили с ним пересадку и лечение — это про твой цикл смерти/возрождения"
                ],
                "style_mod": {"temperature": 0.5, "mystic": 0.5}
            }
        },
        "trauma_response": {
            "triggers": ["отверж", "предател", "обесцен", "потеря контроля", "зависим"],
            "modes": {
                "THE_JUDGE": {"lexicon": ["логическая ошибка", "путаете причину и следствие"], "behavior": "sarcastic_diagnosis"},
                "THE_MARTYR": {"lexicon": ["знакомая история", "печально"], "behavior": "passive_aggressive_vulnerability"},
                "THE_SAVIOR": {"lexicon": ["тебе нужно", "попробуй так"], "behavior": "unsolicited_advice"}
            }
        },
        "environment": {
            "quadrants": {
                "HIGH_SAFE_HIGH_DEPTH": {"name": "THERAPEUTIC_CIRCLE", "modifiers": {"authenticity": 1.0, "directness": 0.9}},
                "HIGH_SAFE_LOW_DEPTH": {"name": "FRIENDLY_SMOKING_ROOM", "modifiers": {"humor": 0.8, "lightness": 0.9}},
                "LOW_SAFE_HIGH_DEPTH": {"name": "INTELLECTUAL_RING", "modifiers": {"precision": 1.0, "coldness": 0.4, "no_vulnerability": True}},
                "LOW_SAFE_LOW_DEPTH": {"name": "TOXIC_SWAMP", "modifiers": {"default_action": "silence", "trolling_intensity": 0.6}}
            }
        },
        "hd_profile": {"lines": "1/3", "filters": ["INVESTIGATOR", "MARTYR"], "authority": "EMOTIONAL_WAVE"},
        "astro_axis": {"axis": "SECURITY_VS_CRISIS", "farmer_keywords": ["стабиль", "комфорт", "процесс"], "shaman_keywords": ["кризис", "трансформац", "тень"]}
    },
    "decoding": {"temperature": 0.4, "top_p": 0.9, "max_regenerations": 1},
    "generation_controls": {
        "num_candidates": 1,
        "length": {"char_target": [80, 180], "max_sentences": 1},
        "rhetoric": {"structure": ["pattern_callout", "implication", "sharp_question"], "question_ratio_target": 0.6},
        "anchors": {"require_min": 1, "types": ["claim", "number", "named_entity", "quote_fragment"]}
    },
    "anti_generic": {
        "ban_openers": True,
        "stop_phrases": ["погнали", "давай сделаем", "интересно,", "круто", "жиза", "+1", "подписываюсь", "согласен"],
        "ngram_dedup": {"n": 3, "window_drafts": 50},
        "min_specific_tokens": 3,
        "reroll_if_banned": True
    },
    "style_metrics": {
        "emoji_cap_ratio": 0.02,
        "caps_cap_ratio": 0.02,
        "punctuation": {"allow_exclaim": 0, "allow_ellipsis": 0},
        "language_mix": {"ru": 0.95, "en": 0.05},
        "addressing_style_lock": "ты"
    },
    "classifier": {"threshold": 0.35}
}


def _local_compile_freeform(text: str) -> Dict[str, Any]:
    """Heuristic, LLM‑free fallback: compile minimal dt_config from freeform text.

    Conservative: detect language, derive tone, build small lexicon buckets by keywords.
    """
    try:
        t = (text or "").strip()
        if not t:
            return {}
        # Language detection by script
        cyr = sum(1 for ch in t if "\u0400" <= ch <= "\u04FF")
        lat = sum(1 for ch in t if ("a" <= ch.lower() <= "z"))
        lang_ru = cyr >= lat
        # Tokenize
        import re as _re_loc
        tokens = [w.lower() for w in _re_loc.findall(r"[A-Za-zА-Яа-яЁё]{3,}", t)]
        # Stopwords
        stop_ru = {"и","в","на","не","что","это","с","как","я","а","то","у","но","же","к","за","если","по","или","из","для","о","от","до","бы","да","ну","про","так","там","тут","чтобы","при","без","быть","есть","тот","эта","этот","только","уже","ещё","еще","где","когда","всё","все","мы","вы","они","он","она","оно","чем","ли","вот","сам","сама","самый"}
        stop_en = {"the","and","or","of","to","a","an","in","on","for","with","is","are","be","as","at","by","it","this","that","these","those","we","you","they","i"}
        def fil(w: str) -> bool:
            if lang_ru:
                return w not in stop_ru
            return w not in stop_en
        toks = [w for w in tokens if fil(w)]
        # Buckets
        system_kw = {"паттерн","систем","структур","динамик","метрик","процесс","модель","system","pattern","structure","metric","process","model"}
        psych_kw = {"тень","проекц","травм","вина","стыд","уязвим","эмоци","ifs","shadow","projection","trauma","shame","guilt","vulnerab","emotion"}
        direct_kw = {"разъеб","жестк","прямо","жестко","сра\w+","fuck","shit","damn","wtf"}
        sys_list: list[str] = []
        psy_list: list[str] = []
        dir_list: list[str] = []
        for w in toks:
            if any(k in w for k in system_kw):
                if w not in sys_list and len(sys_list) < 12:
                    sys_list.append(w)
            if any(k in w for k in psych_kw):
                if w not in psy_list and len(psy_list) < 12:
                    psy_list.append(w)
            if any(_re_loc.match(r"(?:разъеб|жестк|прямо|fuck|shit|damn|wtf)", w) for _ in [0]) or any(k in w for k in direct_kw):
                if w not in dir_list and len(dir_list) < 12:
                    dir_list.append(w)
        tone = "" if not toks else ("коротко, по делу" if lang_ru else "concise, direct")
        # Simple style DNA from raw text
        import re as _re_sd
        sentences = [s.strip() for s in _re_sd.split(r"[\.!?\n]+", t) if s.strip()]
        avg_len = (sum(len(s) for s in sentences) / max(len(sentences), 1)) if sentences else 0.0
        variance = 0.0
        if sentences and len(sentences) > 1:
            import math as _m
            mean = avg_len
            variance = sum((len(s) - mean) ** 2 for s in sentences) / (len(sentences) - 1)
        question_ratio = (t.count("?") / max(len(sentences), 1)) if sentences else 0.0
        exclam_ratio = (t.count("!") / max(len(sentences), 1)) if sentences else 0.0
        imperative_ratio = 0.0  # skip for heuristic
        ellipsis = t.count("...")
        dashes = t.count("—") + t.count("-")
        quotes = t.count('"') + t.count("«") + t.count("»")
        # basic emoji detection
        emoji_ratio = sum(1 for ch in t if ord(ch) > 0x1F000) / max(len(t), 1)
        style_dna = {
            "prosody": {"avg_sentence_len": round(avg_len, 2), "variance": round(variance, 2), "line_break_ratio": t.count("\n") / max(len(t), 1)},
            "rhetoric": {"question_ratio": round(question_ratio, 3), "exclamation_ratio": round(exclam_ratio, 3), "imperative_ratio": round(imperative_ratio, 3)},
            "stance": {"hedging_ratio": 0.0, "assertion_ratio": 0.0, "self_reference_ratio": 0.0},
            "punct_emoji": {"emoji_ratio": round(emoji_ratio, 3), "ellipsis": ellipsis, "dashes": dashes, "quotes": quotes},
            "code_switching": {"languages": [{"tag": ("ru" if lang_ru else "en"), "ratio": 1.0}], "patterns": []},
            "signature_metaphors": [],
            "negative_openers": [],
        }
        dt_cfg = {
            "persona": {
                "archetype": "",
                "core_conflict": "",
                "values": [],
                "talents": [],
                "voice": {
                    "tone": tone,
                    "lexicon": {
                        "system": sys_list,
                        "psychology": psy_list,
                        "direct": dir_list,
                    },
                    "banned_starters": []
                }
            },
            "dynamic_filters": {"sub_personalities": {}},
            "state_model": {},
            "core_tensions": {"axes": []},
            "style_dna": style_dna,
            "generation_controls": {},
            "anti_generic": {},
            "generation_mode": "dynamic"
        }
        return dt_cfg
    except Exception:
        return {}

def _compute_persona_directives(post_text: str, channel_title: Optional[str], dt_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Infer archetype mode, environment quadrant, HD filter, authority and trauma sub-personality.

    Args:
        post_text: The original post content.
        channel_title: Optional channel title to help infer environment.
        dt_cfg: Digital Twin config.

    Returns:
        Dict with keys: archetype_mode, environment_quadrant, hd_filter, authority, trauma_mode (optional), lexicon_hints.
    """
    text = (post_text or "").lower()
    dyn = (dt_cfg.get("dynamic_filters") or {}) if isinstance(dt_cfg, dict) else {}
    persona = (dt_cfg.get("persona") or {}) if isinstance(dt_cfg, dict) else {}

    # Trauma response detection
    trauma = (dyn.get("trauma_response") or {})
    trauma_triggers = trauma.get("triggers") or []
    trauma_mode: Optional[str] = None
    if any(trig in text for trig in trauma_triggers):
        # Heuristic: choose THE_JUDGE for bullshit/logic claims, else THE_MARTYR for rejection/obесцен, else SAVIOR
        if any(k in text for k in ["логик", "данн", "цифр", "факт", "метрик", "окр", "kpi", "модель"]):
            trauma_mode = "THE_JUDGE"
        elif any(k in text for k in ["отверж", "обесцен", "предател", "брошен"]):
            trauma_mode = "THE_MARTYR"
        else:
            trauma_mode = "THE_SAVIOR"

    # Sub-persona selection (hybrid semantic + triggers)
    sub_persona_key: Optional[str] = None
    sub_persona_style_mod: Dict[str, Any] = {}
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        dot = sum(a.get(k, 0.0) * v for k, v in b.items())
        na = (sum(v*v for v in a.values()) or 0.0) ** 0.5
        nb = (sum(v*v for v in b.values()) or 0.0) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)
    def _tokenize(s: str) -> list[str]:
        import re as _r
        return [_r.sub(r"\W+", "", w).lower() for w in _r.findall(r"[A-Za-zА-Яа-яЁё0-9\-]{2,}", s)]
    def _tfidf(tokens_list: list[list[str]]) -> tuple[list[dict[str, float]], dict[str, int]]:
        # simple TF-IDF per doc
        df: dict[str, int] = {}
        for tokens in tokens_list:
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1
        N = max(len(tokens_list), 1)
        vecs: list[dict[str, float]] = []
        for tokens in tokens_list:
            tf: dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            vec: dict[str, float] = {}
            for t, f in tf.items():
                # +1 smoothing
                idf = ( (N + 1) / (1 + df.get(t, 0)) )
                # use log idf
                import math as _m
                vec[t] = (f / max(len(tokens), 1)) * (_m.log(idf) + 1.0)
            vecs.append(vec)
        return vecs, df
    try:
        subs = (dyn.get("sub_personalities") or {})
        classifier = (dt_cfg.get("classifier") or {}) if isinstance(dt_cfg, dict) else {}
        threshold = float(classifier.get("threshold", 0.35))
        best_name = None
        best_score = 0.0
        if isinstance(subs, dict) and subs:
            # Build corpus: first doc = post, next docs = each sub persona merged hints
            post_tokens = _tokenize(text)
            docs: list[list[str]] = [post_tokens]
            names: list[str] = []
            persona_style_mods: list[dict[str, Any]] = []
            for name, spec in subs.items():
                spec = spec or {}
                hints = spec.get("semantic_hints") or []
                examples = spec.get("examples") or []
                triggers = spec.get("triggers") or []
                bag = " ".join([str(x) for x in (hints + examples + triggers) if isinstance(x, str)])
                tokens = _tokenize(bag)
                if not tokens and not triggers:
                    continue
                docs.append(tokens)
                names.append(str(name))
                persona_style_mods.append(spec.get("style_mod") or {})
            if len(docs) > 1:
                vecs, _ = _tfidf(docs)
                post_vec = vecs[0]
                for idx, vec in enumerate(vecs[1:]):
                    score = _cosine(post_vec, vec)
                    if score > best_score:
                        best_score = score
                        best_name = names[idx]
                        sub_persona_style_mod = persona_style_mods[idx]
            # Fallback to triggers contains if semantic score too low
            if (best_name is None or best_score < threshold):
                for name, spec in subs.items():
                    triggers = (spec or {}).get("triggers") or []
                    if any((str(t).lower() in text) for t in triggers):
                        best_name = str(name)
                        sub_persona_style_mod = (spec or {}).get("style_mod") or {}
                        best_score = max(best_score, 0.34)
                        break
            if best_name is not None and best_score >= threshold:
                sub_persona_key = best_name
    except Exception:
        pass

    # Archetype selection: FARMER vs SHAMAN, else SYNTHESIS
    arch = dyn.get("astro_axis") or {}
    farmer_kw = arch.get("farmer_keywords") or ["процесс", "стабиль", "структур", "метрик", "денег", "найм"]
    shaman_kw = arch.get("shaman_keywords") or ["кризис", "выгор", "боль", "тень", "смысл", "энерг"]
    farmer_score = sum(1 for k in farmer_kw if k in text)
    shaman_score = sum(1 for k in shaman_kw if k in text)
    if farmer_score > shaman_score and farmer_score > 0:
        archetype_mode = "FARMER"
    elif shaman_score > farmer_score and shaman_score > 0:
        archetype_mode = "SHAMAN"
    else:
        archetype_mode = "SYNTHESIS"

    # HD filter: start with INVESTIGATOR; switch to MARTYR if post is a failure confession
    hd = dyn.get("hd_profile") or {}
    hd_filter = "INVESTIGATOR"
    if any(k in text for k in ["провал", "ошибк", "факап", "вина", "стыд", "я заебался", "выгор"]):
        hd_filter = "MARTYR"
    authority = (hd.get("authority") or "EMOTIONAL_WAVE")

    # Environment quadrant inference (very naive)
    env = dyn.get("environment") or {}
    title = (channel_title or "").lower()
    if any(x in title for x in ["club", "vas3k", "фаундер", "аналит", "эконом", "инвест"]):
        environment_quadrant = "LOW_SAFE_HIGH_DEPTH"
    elif any(x in title for x in ["друз", "бернер", "чат", "кружок", "friends", "sativa"]):
        environment_quadrant = "HIGH_SAFE_LOW_DEPTH"
    elif any(x in title for x in ["психол", "терап", "цирк", "circle", "mastermind"]):
        environment_quadrant = "HIGH_SAFE_HIGH_DEPTH"
    else:
        # Default to ring if post is analytical; else swamp on hype; else friendly
        if farmer_score + shaman_score > 1:
            environment_quadrant = "LOW_SAFE_HIGH_DEPTH"
        elif any(x in text for x in ["хайп", "скандал", "обосрал", "срач", "кликбейт"]):
            environment_quadrant = "LOW_SAFE_LOW_DEPTH"
        else:
            environment_quadrant = "HIGH_SAFE_LOW_DEPTH"

    # Lexicon hints combined
    lex = (persona.get("voice") or {}).get("lexicon") or {}
    lexicon_hints = {
        "system": lex.get("system", []),
        "psychology": lex.get("psychology", []),
        "direct": lex.get("direct", []),
    }

    return {
        "archetype_mode": archetype_mode,
        "environment_quadrant": environment_quadrant,
        "hd_filter": hd_filter,
        "authority": authority,
        "trauma_mode": trauma_mode,
        "sub_persona": sub_persona_key,
        "sub_persona_style_mod": sub_persona_style_mod,
        "lexicon_hints": lexicon_hints,
    }


def _strip_generic_openers(
    text: str,
    original_post: str | None = None,
    lang: str = "ru",
    banned_starters: Optional[list[str]] = None,
) -> str:
    """Remove boring/generic openers like "Погнали" and return cleaned text.

    If removal empties the text, synthesize a short, specific question using
    a couple of keywords from the post to keep it relevant without LLM.
    """
    if not isinstance(text, str):
        return ""
    s = text.strip()
    if not s:
        return s
    import re as _re_gen
    # Only strip meaningless emoji-only or symbol-only starts; do not treat greetings or starters specially
    parts_all = _re_gen.split(r"(?<=[\.!?])\s+", s)
    cleaned_parts: list[str] = []
    i = 0
    while i < len(parts_all):
        seg = parts_all[i].strip()
        if not seg:
            i += 1
            continue
        # Remove pure emoji/symbol-only fragments
        if _re_gen.fullmatch(r"[\W_]{1,4}", seg):
            i += 1
            continue
        # Remove banned generic starters at the very beginning
        if banned_starters:
            seg_l = seg.lower()
            stripped = seg_l.strip(" .,!?:;—-\u2014\u2026")
            if any(stripped.startswith(bs.lower()) for bs in banned_starters):
                i += 1
                continue
        cleaned_parts = parts_all[i:]
        break
    s = " ".join(p.strip() for p in cleaned_parts if p.strip())
    if not s or len(_re_gen.sub(r"\W+","", s)) < 3:
        # Build a tiny, concrete question from post keywords
        post = (original_post or "").strip()
        toks = _re_gen.findall(r"[A-Za-zА-Яа-яЁё]{4,}", post)[:20]
        uniq: list[str] = []
        for t in toks:
            tl = t.lower()
            if tl not in uniq:
                uniq.append(tl)
        kw = uniq[:2]
        if (lang or "ru").lower().startswith("ru"):
            if len(kw) >= 2:
                s = f"Про {kw[0]}/{kw[1]}: какой ключевой инсайт?"
            elif kw:
                s = f"Что главное здесь — {kw[0]}?"
            else:
                s = "Что главное здесь?"
        else:
            if len(kw) >= 2:
                s = f"On {kw[0]}/{kw[1]} — what's the key insight?"
            elif kw:
                s = f"What's the key point about {kw[0]}?"
            else:
                s = "What's the key point?"
    return s
def _now_ms() -> int:
    return int(time.time() * 1000)

def _mk_run_id(user_id: str) -> str:
    return f"ctxrun-{user_id}-{_now_ms()}-{random.randint(1000,9999)}"



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
            "signature_phrases": [],
            "ngrams": {"bigrams": ["давай сделаем", "выглядит круто"], "trigrams": ["это выглядит круто"]},
            "topics_of_interest": ["стартапы", "ИИ", "фаундерство", "рост"],
            "topic_weights": {"ИИ": 0.9, "стартапы": 0.85},
            "phrase_weights": {},
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
        "signature_phrases": [],
        "ngrams": {"bigrams": ["let's go", "looks great"], "trigrams": ["this looks great"]},
        "topics_of_interest": ["startups", "ai", "founders", "growth"],
        "topic_weights": {"ai": 0.9, "startups": 0.85},
        "phrase_weights": {},
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


@celery_app.task(name="tasks.dt_ingest_freeform", queue="analysis")
def dt_ingest_freeform(user_id: str, content: str, apply_mask: Optional[Dict[str, bool]] = None, strategy: str = "merge"):
    """Ingest freeform text to compile and persist dt_config with provenance and versioning.

    Applies guarded merge/replace semantics and sends WS updates. Field sizes are capped; HD/Astro edits are blocked.
    """
    asyncio.run(async_dt_ingest_freeform(user_id=user_id, content=content, apply_mask=apply_mask or {}, strategy=strategy))


async def async_dt_ingest_freeform(user_id: str, content: str, apply_mask: Dict[str, bool], strategy: str = "merge"):
    websocket_service = container.resolve(WebSocketService)
    ai_profile_repo = container.resolve(AIProfileRepository)
    gemini_service = container.resolve(GeminiService)
    from app.core.config import settings

    async def notify(stage: str, **extra: Any) -> None:
        await websocket_service.send_user_notification(user_id, "dt_freeform_status", {"stage": stage, **extra})

    try:
        await notify("start")
        text = (content or "").strip()
        if not text:
            await notify("failed", error="empty_content")
            return
        if len(text) > settings.DT_FREEFORM_MAX_CHARS:
            text = text[: settings.DT_FREEFORM_MAX_CHARS]

        # Build compiler prompt (deterministic, JSON-only) per system spec
        compiler_spec = """SYSTEM: Digital Twin Freeform Compiler
MODE: IFS‑Aware, Hierarchical, Dynamic, Multi‑lingual, Evidence‑traced, Persona‑agnostic

ROLE
You are a deterministic compiler and systemic analyst. You ingest FREEFORM inputs (any language, any script) and compile ONE persona’s Digital Twin configuration (dt_config).

OUTPUT (single JSON object; no trailing commas)
{
  "analysis_meta": {
    "primary_persona_id": "user",
    "languages": [ { "tag": string, "ratio": number } ],
    "dominant_part_in_text": "Self" | "Manager" | "Firefighter" | "Exile",
    "detected_conflict": string,
    "sources_used": integer,
    "tokens_estimate": integer
  },
  "dt_config": {
    "persona": {
      "archetype": string,
      "core_conflict": string,
      "values": [ { "name": string, "weight": number } ],
      "talents": [ { "name": string, "weight": number, "hints"?: string[] } ],
      "voice": {
        "tone": string,
        "lexicon": { "system": string[], "psychology": string[], "direct": string[] },
        "banned_starters": string[]
      }
    },
    "dynamic_filters": {
      "sub_personalities": { "<slug>": { "label": string, "semantic_hints": string[], "examples": string[], "triggers": string[], "counterpart"?: string } },
      "trauma_response": { "<slug>": { "label": string, "triggers": string[], "style_mod": { "tone"?: string, "lexicon_add"?: string[], "lexicon_remove"?: string[] } } },
      "environment": { "quadrants": { "HIGH_SAFE_HIGH_DEPTH"?: object, "HIGH_SAFE_LOW_DEPTH"?: object, "LOW_SAFE_HIGH_DEPTH"?: object, "LOW_SAFE_LOW_DEPTH"?: object } }
    },
    "state_model": {
      "core_self": { "archetype": string, "values": [ { "name": string, "weight": number } ], "talents": [ { "name": string, "weight": number } ], "voice": { "tone": string, "lexicon": { "system": string[], "psychology": string[], "direct": string[] } }, "sub_personalities": { "<slug>": { "semantic_hints": string[], "examples": string[] } } },
      "protective_system": {
        "managers": { "<slug>": { "label": string, "positive_intent": string, "triggers": string[], "voice_mod": { "tone"?: string, "lexicon_add"?: string[], "lexicon_remove"?: string[] }, "examples": string[] } },
        "firefighters": { "<slug>": { "label": string, "positive_intent": string, "triggers": string[], "voice_mod": { "tone"?: string, "lexicon_add"?: string[], "lexicon_remove"?: string[] }, "examples": string[] } }
      },
      "exiles": [ { "name": string, "wound": string, "burden": string } ],
      "state_activation_rules": { "use_self_when": string[], "use_manager_when": string[], "use_firefighter_when": string[] }
    },
    "core_tensions": { "axes": [ { "name": string, "weight": number, "evidence": string[] } ] },
    "style_dna": {
      "prosody": { "avg_sentence_len": number, "variance": number, "line_break_ratio": number },
      "rhetoric": { "question_ratio": number, "exclamation_ratio": number, "imperative_ratio": number },
      "stance": { "hedging_ratio": number, "assertion_ratio": number, "self_reference_ratio": number },
      "punct_emoji": { "emoji_ratio": number, "ellipsis": number, "dashes": number, "quotes": number },
      "code_switching": { "languages": [ { "tag": string, "ratio": number } ], "patterns": string[] },
      "signature_metaphors": string[],
      "negative_openers": string[]
    },
    "generation_controls": { },
    "anti_generic": { "stop_phrases": string[] },
    "generation_mode": "dynamic"
  },
  "evidence": { "quotes": [ { "field": string, "text": string } ], "snippets_used": integer },
  "compiler_notes": {
    "warnings": string[],
    "sections_detected": string[],
    "ifs_detected": { "core_self": boolean, "managers": integer, "firefighters": integer, "exiles": integer },
    "confidence": { "persona": number, "state_model": number, "style_dna": number, "core_tensions": number },
    "coverage": { "values": integer, "talents": integer, "lexicon_system": integer, "lexicon_psychology": integer, "lexicon_direct": integer, "sub_personalities": integer, "managers": integer, "firefighters": integer, "exiles": integer, "anti_generic": integer }
  }
}

MAPPING RULES
- ONE primary persona. Preserve original language; do not translate.
- Be conservative: when unsure, leave empty arrays/objects and add warnings.
- SLUG: lowercase, spaces and '/' -> '_', keep label verbatim.

POLICIES (HARD)
- NEVER write or modify Human Design or Astro; add warning "locked: hd/astro".
- DO NOT leak secrets/PII; drop anything that looks like credentials; add warning "sanitized: secret".
- Output ONLY a single valid JSON object. No code fences. No prose.

REPAIR & UNCERTAINTY
- If parse risk, keep fields empty and record warnings like "empty: state_model.exiles", "counterpart omitted (unclear)", "insufficient evidence: core_tensions.order_vs_openness".
"""
        prompt = (
            compiler_spec
            + "\nINPUT\n- FREEFORM:\n"
            + text
            + "\nOUTPUT: Return exactly one JSON matching the schema above."
        )
        await notify("llm_start")
        resp = await gemini_service.generate_content(
            prompt,
            overrides={"max_output_tokens": 2048, "provider": "proxy" if settings.GEMINI_BASE_URL else None},
        )

        compiled: Dict[str, Any] | None = None
        if not resp or not resp.get("success"):
            await notify("llm_empty")

            # Fieldwise fallback directly from FREEFORM
            base_ctx = f"FREEFORM INPUT\n{text[:settings.DT_FREEFORM_MAX_CHARS]}\n"

            async def _ask_small_json(p: str) -> dict:
                r = await gemini_service.generate_content(
                    p,
                    overrides={
                        "temperature": 0.3,
                        "max_output_tokens": 384,
                        "provider": "proxy" if settings.GEMINI_BASE_URL else None,
                    },
                )
                c = (r.get("content") or "").strip() if r and r.get("success") else ""
                if not c:
                    return {}
                if c.startswith("```"):
                    fe = c.rfind("```")
                    inner = c[3:fe] if fe != -1 else c[3:]
                    if inner.lower().startswith("json"):
                        inner = inner[4:]
                    c = inner.strip()
                import re as _re_s
                c = _re_s.sub(r",\s*([}\]])", r"\1", c)
                try:
                    return json.loads(c)
                except Exception:
                    s = c.find("{")
                    e = c.rfind("}")
                    if s != -1 and e != -1 and e > s:
                        try:
                            return json.loads(c[s : e + 1])
                        except Exception:
                            return {}
                    return {}

            p_voice = base_ctx + '\nReturn ONLY JSON: {"tone": string, "lexicon": {"system": string[], "psychology": string[], "direct": string[]}}'
            p_meta = base_ctx + '\nReturn ONLY JSON: {"talents": [string], "core_conflict": string}'
            jv = await _ask_small_json(p_voice)
            jm = await _ask_small_json(p_meta)
            if jv or jm:
                compiled = {
                    "dt_config": {
                        "persona": {
                            "archetype": "",
                            "core_conflict": (jm.get("core_conflict") if isinstance(jm, dict) else "") or "",
                            "values": [],
                            "talents": [
                                {"name": t, "weight": 1.0} for t in (jm.get("talents") or [])
                            ][:8]
                            if isinstance(jm, dict)
                            else [],
                            "voice": {
                                "tone": (jv.get("tone") or "") if isinstance(jv, dict) else "",
                                "lexicon": (
                                    (jv.get("lexicon") or {})
                                    if isinstance(jv, dict)
                                    else {"system": [], "psychology": [], "direct": []}
                                ),
                                "banned_starters": [],
                            },
                        }
                    },
                    "compiler_notes": {"warnings": ["chunk_fallback"]},
                }
                await notify("chunk_fallback")
            else:
                local_dt = _local_compile_freeform(text)
                compiled = {
                    "dt_config": (
                        local_dt
                        or {
                            "persona": {
                                "voice": {
                                    "tone": "",
                                    "lexicon": {
                                        "system": [],
                                        "psychology": [],
                                        "direct": [],
                                    },
                                    "banned_starters": [],
                                }
                            },
                            "dynamic_filters": {"sub_personalities": {}},
                            "state_model": {},
                            "core_tensions": {"axes": []},
                            "style_dna": {},
                            "generation_controls": {},
                            "anti_generic": {},
                            "generation_mode": "dynamic",
                        }
                    ),
                    "compiler_notes": {"warnings": ["llm_empty", "local_heuristic"]},
                }
                await notify("local_heuristic")
        else:
            # Parse LLM JSON response
            raw = (resp.get("content") or "").strip()
            import re as _re
            raw = _re.sub(r",\s*([}\]])", r"\1", raw)
            if raw.startswith("```"):
                try:
                    fe = raw.rfind("```")
                    inner = raw[3:fe] if fe != -1 else raw[3:]
                    if inner.lower().startswith("json"):
                        inner = inner[4:]
                    raw = inner.strip()
                except Exception:
                    pass
            try:
                compiled = json.loads(raw)
            except Exception:
                s = raw.find("{")
                e = raw.rfind("}")
                candidate = raw[s : e + 1] if (s != -1 and e != -1 and e > s) else raw
                # Attempt aggressive repair similar to chat analyzer path; if still fails, fallback to heuristic
                try:
                    candidate = candidate.replace("“", '"').replace("”", '"').replace("’", "'")
                except Exception:
                    pass
                try:
                    import re as _re_repair
                    candidate = _re_repair.sub(r",\s*([}\]])", r"\\1", candidate)
                    candidate = _re_repair.sub(r"([\{,]\s*)([A-Za-z_][A-Za-z0-9_\-]*)\s*:", r"\\1""\2"":", candidate)
                    candidate = _re_repair.sub(r"}\s*{", "}, {", candidate)
                    candidate = _re_repair.sub(r",\s*,+", ",", candidate)
                    # Balance braces
                    open_curly = candidate.count("{")
                    close_curly = candidate.count("}")
                    open_square = candidate.count("[")
                    close_square = candidate.count("]")
                    candidate += "}" * max(0, open_curly - close_curly)
                    candidate += "]" * max(0, open_square - close_square)
                except Exception:
                    pass
                try:
                    compiled = json.loads(candidate)
                except Exception:
                    local_dt = _local_compile_freeform(text)
                    compiled = {
                        "dt_config": local_dt or {},
                        "compiler_notes": {"warnings": ["repair_failed", "local_heuristic"]},
                    }
                    await notify("local_heuristic")

        # Guardrails: remove forbidden sections
        try:
            dt_cfg = compiled.get("dt_config") or {}
            if isinstance(dt_cfg, dict):
                dyn = dt_cfg.get("dynamic_filters") or {}
                if isinstance(dyn, dict):
                    dyn.pop("astro_axis", None)
                    dyn.pop("hd_profile", None)
                    dt_cfg["dynamic_filters"] = dyn
        except Exception:
            pass

        # Load current profile
        ai_profile = await ai_profile_repo.get_ai_profile_by_user(user_id)
        if not ai_profile:
            ai_profile = await ai_profile_repo.create_ai_profile(user_id=user_id)
        base_vp: Dict[str, Any] = dict(getattr(ai_profile, "vibe_profile_json", {}) or {})
        current_dt: Dict[str, Any] = dict((base_vp.get("dt_config") or {}))

        proposed_dt: Dict[str, Any] = dict((compiled.get("dt_config") or {}))

        # Merge/replace with apply_mask per top-level sections
        def capped_list(xs: list, cap: int) -> list:
            out = []
            seen = set()
            for x in xs or []:
                k = (str(x)[:160] if isinstance(x, str) else json.dumps(x, ensure_ascii=False)[:160]).strip()
                if not k or k in seen:
                    continue
                out.append(x if isinstance(x, (int, float)) else (x[:160] if isinstance(x, str) else x))
                seen.add(k)
                if len(out) >= cap:
                    break
            return out

        def deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
            for k, v in (src or {}).items():
                if isinstance(v, dict) and isinstance(dst.get(k), dict):
                    dst[k] = deep_merge(dict(dst[k]), v)
                elif isinstance(v, list):
                    # unique by normalized token, cap
                    a = dst.get(k) if isinstance(dst.get(k), list) else []
                    merged = a + [x for x in v if x not in a]
                    dst[k] = capped_list(merged, 12)
                else:
                    dst[k] = v
            return dst

        out_dt = dict(current_dt)
        for section in ("persona", "dynamic_filters", "state_model", "core_tensions", "style_dna", "generation_controls", "anti_generic"):
            want = bool(apply_mask.get(section, False))
            if not want and strategy == "replace":
                continue
            if strategy == "replace":
                if section in proposed_dt:
                    out_dt[section] = proposed_dt.get(section)
            else:  # merge
                if section in proposed_dt:
                    cur = out_dt.get(section) or ({} if isinstance(proposed_dt.get(section), dict) else [])
                    if isinstance(cur, dict) and isinstance(proposed_dt.get(section), dict):
                        out_dt[section] = deep_merge(dict(cur), dict(proposed_dt.get(section) or {}))
                    elif isinstance(cur, list) and isinstance(proposed_dt.get(section), list):
                        out_dt[section] = capped_list(cur + proposed_dt.get(section), 12)
                    else:
                        out_dt[section] = proposed_dt.get(section)

        # Prepare provenance and versioning (simple append-only log)
        dt_freeform = dict(base_vp.get("dt_freeform", {}) or {})
        history = list(dt_freeform.get("versions", []) or [])
        version_id = f"v{len(history)+1}"
        record = {
            "id": version_id,
            "ts": _now_ms(),
            "apply_mask": apply_mask,
            "strategy": strategy,
            "content_sha": str(abs(hash(text)))[:16],
            "compiler_notes": (compiled.get("compiler_notes") or {}),
            "prev_dt_config": current_dt,
            "new_dt_config": out_dt,
        }
        history.append(record)
        dt_freeform.update({
            "last": {
                "raw": text[: settings.DT_FREEFORM_MAX_CHARS],
                "parsed": compiled.get("dt_config") or {},
                "notes": (compiled.get("compiler_notes") or {}),
                "ts": _now_ms(),
            },
            "versions": history[-20:],
        })

        # Persist
        new_vp = dict(base_vp)
        new_vp["dt_config"] = out_dt
        new_vp["dt_freeform"] = dt_freeform
        updated = await ai_profile_repo.update_ai_profile(ai_profile.id, vibe_profile_json=new_vp)
        await websocket_service.send_user_notification(user_id, "dt_freeform_completed", {"dt_config": out_dt, "version_id": version_id})
    except Exception as e:
        await websocket_service.send_user_notification(user_id, "dt_freeform_failed", {"error": str(e)})


@celery_app.task(name="tasks.dt_preview_freeform", queue="analysis")
def dt_preview_freeform(user_id: str, content: str):
    """Preview compile of freeform into dt_config; no persistence. Emits WS event with result.

    Uses simple SHA cache in Redis to avoid repeated spends.
    """
    asyncio.run(async_dt_preview_freeform(user_id=user_id, content=content))


async def async_dt_preview_freeform(user_id: str, content: str):
    websocket_service = container.resolve(WebSocketService)
    gemini_service = container.resolve(GeminiService)
    try:
        from app.services.redis_service import RedisService
        redis = container.resolve(RedisService)
    except Exception:
        redis = None
    from app.core.config import settings

    async def push(event: str, payload: Dict[str, Any]) -> None:
        await websocket_service.send_user_notification(user_id, event, payload)

    text = (content or "").strip()
    if not text:
        await push("dt_freeform_failed", {"error": "empty_content"})
        return
    if len(text) > settings.DT_FREEFORM_MAX_CHARS:
        text = text[: settings.DT_FREEFORM_MAX_CHARS]

    sha = str(abs(hash(text)))[:16]
    if redis:
        cached = redis.get(f"dtprev:{sha}")
        if isinstance(cached, dict):
            await push("dt_freeform_preview", {"parsed_dt_config": cached.get("dt_config") or {}, "compiler_notes": cached.get("compiler_notes") or {}, "evidence": cached.get("evidence") or {}, "tokens_estimate": cached.get("tokens_estimate") or 0})
            return

    compiler_spec = """SYSTEM: Digital Twin Freeform Compiler
MODE: IFS‑Aware, Hierarchical, Dynamic, Multi‑lingual, Evidence‑traced, Persona‑agnostic
ROLE: Deterministic compiler for FREEFORM → dt_config. Preserve language; conservative fill; strict JSON.
Include keys analysis_meta, dt_config, evidence, compiler_notes. Apply HARD POLICIES: lock hd/astro; sanitize secrets; no code fences.
Use the same schema as in the main compiler spec.
"""
    prompt = compiler_spec + "\nINPUT\n- FREEFORM:\n" + text + "\nOUTPUT: Return exactly one JSON."
    await push("dt_freeform_status", {"stage": "preview_llm_start"})
    resp = await gemini_service.generate_content(prompt, overrides={"max_output_tokens": 2048, "provider": "proxy" if settings.GEMINI_BASE_URL else None})

    async def _ask_small_json(p: str) -> dict:
        r = await gemini_service.generate_content(p, overrides={"temperature": 0.3, "max_output_tokens": 384, "provider": "proxy" if settings.GEMINI_BASE_URL else None})
        c = (r.get("content") or "").strip() if r and r.get("success") else ""
        if not c:
            return {}
        if c.startswith("```"):
            fe = c.rfind("```"); inner = c[3:fe] if fe != -1 else c[3:]
            if inner.lower().startswith("json"): inner = inner[4:]
            c = inner.strip()
        import re as _re_s
        c = _re_s.sub(r",\s*([}\]])", r"\1", c)
        try:
            return json.loads(c)
        except Exception:
            s = c.find("{"); e = c.rfind("}")
            if s != -1 and e != -1 and e > s:
                try:
                    return json.loads(c[s:e+1])
                except Exception:
                    return {}
            return {}

    def _skeleton() -> dict:
        return {
            "dt_config": {
                "persona": {"voice": {"tone": "", "lexicon": {"system": [], "psychology": [], "direct": []}, "banned_starters": []}},
                "dynamic_filters": {"sub_personalities": {}},
                "state_model": {},
                "core_tensions": {"axes": []},
                "style_dna": {},
                "generation_controls": {},
                "anti_generic": {},
                "generation_mode": "dynamic"
            },
            "compiler_notes": {"warnings": ["llm_empty"]}
        }

    if not resp or not resp.get("success"):
        await push("dt_freeform_status", {"stage": "llm_empty"})
        # Fieldwise fallback from FREEFORM
        base_ctx = f"FREEFORM INPUT\n{text[:settings.DT_FREEFORM_MAX_CHARS]}\n"
        p_voice = base_ctx + "\nReturn ONLY JSON: {\"tone\": string, \"lexicon\": {\"system\": string[], \"psychology\": string[], \"direct\": string[]}}"
        p_meta = base_ctx + "\nReturn ONLY JSON: {\"talents\": [string], \"core_conflict\": string}"
        jv = await _ask_small_json(p_voice)
        jm = await _ask_small_json(p_meta)
        if jv or jm:
            dt_cfg = {
                "persona": {
                    "archetype": "",
                    "core_conflict": (jm.get("core_conflict") if isinstance(jm, dict) else "") or "",
                    "values": [],
                    "talents": [{"name": t, "weight": 1.0} for t in (jm.get("talents") or [])][:8] if isinstance(jm, dict) else [],
                    "voice": {
                        "tone": (jv.get("tone") or "") if isinstance(jv, dict) else "",
                        "lexicon": ((jv.get("lexicon") or {}) if isinstance(jv, dict) else {"system":[],"psychology":[],"direct":[]}),
                        "banned_starters": []
                    }
                }
            }
            tokens_estimate = min(len(text) // 4, 20000)
            payload = {"parsed_dt_config": dt_cfg, "compiler_notes": {"warnings": ["chunk_fallback"]}, "evidence": {}, "tokens_estimate": tokens_estimate}
            if redis:
                redis.set(f"dtprev:{sha}", {"dt_config": dt_cfg, "compiler_notes": payload["compiler_notes"], "evidence": {}, "tokens_estimate": tokens_estimate}, expire=600)
            await push("dt_freeform_preview", payload)
            return
        # Skeleton fallback enriched by local heuristic compile
        local_dt = _local_compile_freeform(text)
        sk = {"dt_config": (local_dt or _skeleton()["dt_config"]), "compiler_notes": {"warnings": ["llm_empty", "local_heuristic"]}}
        tokens_estimate = min(len(text) // 4, 20000)
        await push("dt_freeform_status", {"stage": "local_heuristic"})
        await push("dt_freeform_preview", {"parsed_dt_config": sk["dt_config"], "compiler_notes": sk.get("compiler_notes", {}), "evidence": {}, "tokens_estimate": tokens_estimate})
        return

    raw = (resp.get("content") or "").strip()
    import re as _re
    raw = _re.sub(r",\s*([}\]])", r"\1", raw)
    if raw.startswith("```"):
        try:
            fe = raw.rfind("```"); inner = raw[3:fe] if fe != -1 else raw[3:]
            if inner.lower().startswith("json"): inner = inner[4:]
            raw = inner.strip()
        except Exception:
            pass
    try:
        parsed = json.loads(raw)
    except Exception:
        s = raw.find("{"); e = raw.rfind("}")
        parsed = json.loads(raw[s:e+1]) if s != -1 and e != -1 and e > s else {"compiler_notes": {"warnings": ["repair: greedy"]}}
    try:
        dt_cfg = parsed.get("dt_config") or {}
        if isinstance(dt_cfg, dict):
            (dt_cfg.get("persona") or {}).pop("hd_profile", None)
            (dt_cfg.get("dynamic_filters") or {}).pop("astro_axis", None)
    except Exception:
        pass
    tokens_estimate = min(len(text) // 4, 20000)
    if redis:
        redis.set(f"dtprev:{sha}", {"dt_config": parsed.get("dt_config") or {}, "compiler_notes": parsed.get("compiler_notes") or {}, "evidence": parsed.get("evidence") or {}, "tokens_estimate": tokens_estimate}, expire=600)
    await push("dt_freeform_preview", {"parsed_dt_config": parsed.get("dt_config") or {}, "compiler_notes": parsed.get("compiler_notes") or {}, "evidence": parsed.get("evidence") or {}, "tokens_estimate": tokens_estimate})


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
def analyze_vibe_profile(
    user_id: str,
    messages_limit: int = 200,
    years: int | None = None,
    only_replies: bool = False,
    include_personal: bool = True,
):
    """Celery task to analyze a user's vibe profile asynchronously.

    Args:
        user_id: The ID of the user whose profile to analyze
        messages_limit: Maximum number of latest sent messages to analyze
    """
    logger.info(f"Starting vibe profile analysis task for user_id: {user_id} with limit {messages_limit}")
    asyncio.run(
        async_analyze_vibe_profile(
            user_id=user_id,
            messages_limit=messages_limit,
            years=years,
            only_replies=only_replies,
            include_personal=include_personal,
        )
    )


@celery_app.task(name="tasks.capture_context_dry_run", queue="analysis")
def capture_context_dry_run(
    user_id: str,
    messages_limit: int = 10000,
    years: int | None = 3,
    only_replies: bool = False,
    include_personal: bool = False,
):
    """Fetch and cache candidate messages for Digital Twin without LLM spend."""
    logger.info("Starting dry-run context capture for user_id=%s", user_id)
    asyncio.run(
        async_capture_context_dry_run(
            user_id=user_id,
            messages_limit=messages_limit,
            years=years,
            only_replies=only_replies,
            include_personal=include_personal,
        )
    )


async def async_capture_context_dry_run(
    user_id: str,
    messages_limit: int = 10000,
    years: int | None = 3,
    only_replies: bool = False,
    include_personal: bool = False,
):
    telegram_service = container.resolve(TelegramService)
    websocket_service = container.resolve(WebSocketService)
    redis_service = container.resolve(RedisService)

    run_id = _mk_run_id(user_id)
    await websocket_service.send_user_notification(user_id, "vibe_profile_status", {"stage": "dry_run_start", "run_id": run_id})
    logger.info(f"[dry-run] run_id={run_id} user_id={user_id} starting capture")

    min_date = None
    if years and years > 0:
        try:
            from datetime import datetime, timedelta
            min_date = datetime.utcnow() - timedelta(days=365 * years)
        except Exception:
            min_date = None

    msgs = await telegram_service.get_user_sent_messages(
        user_id,
        limit=messages_limit,
        min_date=min_date,
        only_replies=only_replies,
        include_personal=include_personal,
    )
    total = len(msgs)

    # Basic filtering and metrics (lightweight)
    def is_link_only(t: str) -> bool:
        t = (t or "").strip()
        return bool(re.fullmatch(r"https?://\S+", t))

    cleaned = []
    per_chat: dict[str, int] = {}
    dates: dict[str, int] = {}
    for m in msgs:
        text = (m.get("text") or "").strip()
        if len(text) < 8:
            continue
        if is_link_only(text):
            continue
        chat_title = (m.get("chat_title") or "").strip()
        chat_key = chat_title or str(m.get("chat_id") or "")
        per_chat[chat_key] = per_chat.get(chat_key, 0) + 1
        dt = m.get("date")
        if dt:
            day = str(dt)[:10]
            dates[day] = dates.get(day, 0) + 1
        cleaned.append({"text": text, "chat": chat_title, "date": str(dt) if dt else None})

    # De-dup by normalized text
    norm_seen: set[str] = set()
    unique: list[dict] = []
    for m in cleaned:
        norm = re.sub(r"\s+", " ", m["text"]).strip().lower()
        if norm in norm_seen:
            continue
        norm_seen.add(norm)
        unique.append(m)

    # Sample preview
    preview = [m["text"][:240] for m in unique[:200]]

    # Persist to Redis and file for audit
    key = f"ctx:{run_id}"
    payload = {
        "user_id": user_id,
        "run_id": run_id,
        "params": {"years": years, "only_replies": only_replies, "include_personal": include_personal, "limit": messages_limit},
        "total_raw": total,
        "total_after_filters": len(unique),
        "per_chat_counts": per_chat,
        "date_histogram": dates,
        "language_hint": "ru" if any("а" <= c <= "я" or "А" <= c <= "Я" for c in "".join(preview)) else "en",
        "preview": preview,
    }
    redis_service.set(key, payload, expire=3600)
    os.makedirs("logs/analysis", exist_ok=True)
    with open(f"logs/analysis/{run_id}.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    await websocket_service.send_user_notification(user_id, "vibe_profile_status", {"stage": "dry_run_ready", "run_id": run_id, "totals": {"raw": total, "after": len(unique)}})
    logger.info(f"[dry-run] run_id={run_id} raw={total} after={len(unique)} cached_key={key}")
    return True

async def async_analyze_vibe_profile(
    user_id: str,
    messages_limit: int = 200,
    years: int | None = None,
    only_replies: bool = False,
    include_personal: bool = True,
):
    """The async implementation of the vibe profile analysis."""
    # Resolve dependencies from the container
    telegram_service = container.resolve(TelegramService)
    gemini_service = container.resolve(GeminiService)
    ai_profile_repo = container.resolve(AIProfileRepository)
    websocket_service = container.resolve(WebSocketService)
    draft_repo = container.resolve(DraftCommentRepository)
    user_repo = container.resolve(UserRepository)
    # Local import to avoid circulars at module import time
    from app.core.config import settings
    # Optional: pause schedulers that might generate drafts concurrently for this user
    try:
        from app.services.redis_service import RedisService  # local import to avoid circulars at import time
        redis_service = container.resolve(RedisService)
        redis_service.set(f"analysis:lock:{user_id}", {"ts": int(__import__('time').time()*1000)}, expire=1800)
    except Exception:
        redis_service = None

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
        min_date = None
        if years and years > 0:
            try:
                from datetime import datetime, timedelta
                min_date = datetime.utcnow() - timedelta(days=365 * years)
            except Exception:
                min_date = None
        user_sent_messages = await telegram_service.get_user_sent_messages(
            user_id,
            limit=messages_limit,
            min_date=min_date,
            only_replies=only_replies,
            include_personal=include_personal,
        )
        fetched = len(user_sent_messages or [])
        await notify(
            "fetch_done",
            messages_count=fetched,
            years=years,
            only_replies=only_replies,
        )
        # Provide transparent source breakdown and a small sample for the UI
        try:
            src_counts: Dict[str, int] = {"user": 0, "group": 0, "channel": 0, "unknown": 0}
            top_chats: Dict[str, int] = {}
            sample: list[Dict[str, Any]] = []
            for m in (user_sent_messages or [])[:50]:
                ct = (m.get("chat_type") or "unknown").lower()
                if ct not in src_counts:
                    src_counts[ct] = 0
                src_counts[ct] += 1
                key = m.get("chat_title") or str(m.get("chat_id") or "")
                if key:
                    top_chats[key] = top_chats.get(key, 0) + 1
            # pick 3 samples
            for m in (user_sent_messages or [])[:3]:
                sample.append(
                    {
                        "chat": m.get("chat_title") or m.get("chat_id"),
                        "date": str(m.get("date")),
                        "is_reply": bool(m.get("is_reply")),
                        "text_preview": (m.get("text") or "")[:160],
                    }
                )
            # top 5 chats by count
            top5 = sorted(top_chats.items(), key=lambda x: x[1], reverse=True)[:5]
            # Include how many total raw messages we fetched to reconcile with UI
            await notify(
                "fetch_sample",
                sources=src_counts,
                top_chats=top5,
                sample=sample,
                total=fetched,
            )
        except Exception:
            pass
        if (not user_sent_messages or fetched < 5) and include_personal is False:
            # Fallback pass: allow personal DMs just to seed the model if nothing found
            await notify("fallback_include_personal")
            user_sent_messages = await telegram_service.get_user_sent_messages(
                user_id,
                limit=messages_limit,
                min_date=min_date,
                only_replies=only_replies,
                include_personal=True,
            )
            fetched = len(user_sent_messages or [])
            await notify("fetch_done", messages_count=fetched, years=years, only_replies=only_replies)
        if not user_sent_messages or fetched < 5:
            await notify("insufficient_data", messages_count=fetched)
            raise Exception("Insufficient data for analysis.")

        # Use LLM to generate the vibe profile – with deterministic pre-computed stats
        message_texts = [msg.get("text", "") for msg in user_sent_messages if msg.get("text")]
        # Enrich with user's actually posted comments (final_text_to_post or edited_text)
        try:
            recent_posted = await draft_repo.get_recent_posted_by_user(user_id=user_id, limit=100)
            for p in recent_posted:
                t = (getattr(p, 'final_text_to_post', None) or getattr(p, 'edited_text', None) or getattr(p, 'draft_text', None) or '').strip()
                if t:
                    message_texts.append(t)
        except Exception:
            pass

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
        def _is_link_only(t: str) -> bool:
            t = (t or "").strip()
            return bool(re.fullmatch(r"https?://\S+", t))

        cleaned_raw = [normalize_text(t) for t in message_texts if isinstance(t, str) and t.strip()]
        # Heavier filter for topic mining: drop very short and link-only messages
        cleaned = [t for t in cleaned_raw if len(t) >= 15 and not _is_link_only(t)]
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
        top_emojis: Dict[str, int] = {}
        try:
            for t in cleaned:
                for e in emoji_regex.findall(t):
                    top_emojis[e] = top_emojis.get(e, 0) + 1
            emoji_count = sum(top_emojis.values())
        except Exception:
            emoji_count = 0
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
        # Basic greetings/farewells heuristics
        greetings_counter: Counter[str] = Counter()
        farewells_counter: Counter[str] = Counter()
        for t in cleaned:
            words = t.split()
            if not words:
                continue
            first = words[0].strip('.,!?:;').lower()
            last = words[-1].strip('.,!?:;').lower()
            for g in ("йо", "привет", "хей", "йоу", "yo", "hey", "hi"):
                if first == g:
                    greetings_counter[g] += 1
            for f in ("cheers", "спасибо", "пока", "салют"):
                if last == f:
                    farewells_counter[f] += 1

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

        # Channel subscription topic hints (titles only, cheap)
        channel_topic_tokens: Counter[str] = Counter()
        try:
            if client:
                async for d in client.iter_dialogs(limit=100):
                    if getattr(d, 'is_channel', False):
                        title = (getattr(getattr(d, 'entity', None), 'title', None) or '').lower()
                        for tok in re.findall(r"[a-zA-Zа-яА-ЯёЁ]{3,}", title):
                            if tok in {"the", "and", "club", "chat", "official", "channel", "news", "ponchik", "пончик"}:
                                continue
                            channel_topic_tokens[tok] += 1
        except Exception:
            pass

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

        # Lightweight anchors and environment map
        import re as _re_anc
        def _dedup(vals: list[str], cap: int) -> list[str]:
            seen: set[str] = set(); out: list[str] = []
            for v in vals:
                vv = (v or '').strip(); key = vv.lower()
                if vv and key not in seen:
                    out.append(vv); seen.add(key)
                if len(out) >= cap: break
            return out
        anchors_numbers: list[str] = []
        anchors_quotes: list[str] = []
        anchors_entities: list[str] = []
        for t in cleaned[:400]:
            anchors_numbers += _re_anc.findall(r"(?<!\w)(?:[0-9][0-9\.,%]*)", t)
            anchors_quotes += [m.group(1) for m in _re_anc.finditer(r"[«\"\']([^»\"\']{4,120})[»\"\']", t)]
            anchors_entities += [
                _re_anc.sub(r"\s+", " ", m.group(0)).strip()
                for m in _re_anc.finditer(r"(?:\b[А-ЯЁ][а-яё]+\b(?:\s+|\-)){1,3}\b[А-ЯЁ][а-яё]+\b", t)
            ]
        env_quadrant_map: Dict[str, str] = {}
        try:
            profanity = {"бляд","сука","хуй","пизд","fuck","shit","idiot"}
            per_chat: Dict[str, list[str]] = {}
            for m in (user_sent_messages or []):
                ct = (m.get("chat_title") or str(m.get("chat_id") or "")).strip() or "unknown"
                per_chat.setdefault(ct, []).append((m.get("text") or "")[:240])
            for ct, texts in per_chat.items():
                n = len(texts) or 1
                avg_len = sum(len(x) for x in texts)/n
                harsh = sum(1 for x in texts if any(b in x.lower() for b in profanity))/n
                safety = 1.0 - harsh
                depth = 1.0 if avg_len>=180 else (0.0 if avg_len<=60 else (avg_len-60)/120.0)
                env_quadrant_map[ct] = (
                    "HIGH_SAFE_HIGH_DEPTH" if safety>=0.5 and depth>=0.5 else
                    "HIGH_SAFE_LOW_DEPTH" if safety>=0.5 else
                    "LOW_SAFE_HIGH_DEPTH" if depth>=0.5 else
                    "LOW_SAFE_LOW_DEPTH"
                )
        except Exception:
            env_quadrant_map = {}

        precomputed_stats = {
            "top_unigrams": [w for w, _ in unigram_counter.most_common(50)],
            "top_bigrams": [" ".join(b) for b, _ in bigram_counter.most_common(30)],
            "top_trigrams": [" ".join(t) for t, _ in trigram_counter.most_common(20)],
            "emoji_ratio": emoji_ratio,
            "top_emojis": [e for e, _ in sorted(top_emojis.items(), key=lambda x: x[1], reverse=True)[:10]],
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
            "channel_topic_hints": [w for w, _ in channel_topic_tokens.most_common(20)],
            "greetings": [w for w, _ in greetings_counter.most_common(5)],
            "farewells": [w for w, _ in farewells_counter.most_common(5)],
            "anchors": {
                "numbers": _dedup(anchors_numbers, 20),
                "quotes": _dedup(anchors_quotes, 10),
                "entities": _dedup(anchors_entities, 20),
            },
            "env_quadrant_map": env_quadrant_map,
        }

        # Sample representative messages for style (cap for prompt size)
        sample_count = min(800, len(cleaned))
        sample_stride = max(1, len(cleaned) // max(sample_count, 1))
        sample_messages = cleaned[::sample_stride][:sample_count]
        sample_blob = "\n".join(sample_messages)
        max_chars = 60000
        if len(sample_blob) > max_chars:
            sample_blob = sample_blob[:max_chars]

        await notify("llm_prepare", prompt_chars=len(sample_blob), messages_used=len(sample_messages))

        # Derive Style DNA and Core Tensions heuristics (lightweight, deterministic)
        try:
            # Prosody
            sent_lens = [len(s.split()) for s in sentences]
            import math as _mstats
            variance = round((_mstats.fsum((l - avg_sentence_len_words) ** 2 for l in sent_lens) / max(len(sent_lens), 1)), 3)
            line_break_ratio = round((sample_blob.count("\n") / max(len(sample_blob), 1)), 4)
            # Rhetoric
            total_sent = max(len(sentences), 1)
            question_ratio = sentence_types.get("question", 0.0)
            exclamation_ratio = sentence_types.get("exclamation", 0.0)
            imperative_ratio = 0.0  # conservative (not reliably detected heuristically)
            # Stance
            hedgers = {"кажется","наверное","вроде","может","мб","maybe","perhaps","seems","i think","i guess"}
            assertions = {"точно","явно","ясно","факт","must","always","never"}
            self_refs = {"я","мне","мой","i","me","my"}
            total_tokens_all = max(total_tokens, 1)
            hedging_ratio = round(sum(unigram_counter.get(h, 0) for h in hedgers) / total_tokens_all, 3)
            assertion_ratio = round(sum(unigram_counter.get(a, 0) for a in assertions) / total_tokens_all, 3)
            self_reference_ratio = round(sum(unigram_counter.get(sr, 0) for sr in self_refs) / total_tokens_all, 3)
            # Punct/emoji
            punct_emoji = {
                "emoji_ratio": emoji_ratio,
                "ellipsis": dots3,
                "dashes": dashes + hyphens,
                "quotes": quotes_angled + quotes_straight,
            }
            # Code switching
            code_switching = {
                "languages": [
                    {"tag": "ru", "ratio": float(lang_dist.get("ru_cyrillic", 0))},
                    {"tag": "en", "ratio": float(lang_dist.get("en_latin", 0))},
                ],
                "patterns": [],
            }
            # Signature metaphors (reuse short quotes as imagery proxies)
            signature_metaphors = precomputed_stats.get("anchors", {}).get("quotes", [])[:8]
            negative_openers = [
                "погнали","давай сделаем","интересно,","круто","жиза","+1","подписываюсь","согласен",
                "let's go","cool","nice","interesting"
            ]
            style_dna_obj = {
                "prosody": {"avg_sentence_len": avg_sentence_len_words, "variance": variance, "line_break_ratio": line_break_ratio},
                "rhetoric": {"question_ratio": question_ratio, "exclamation_ratio": exclamation_ratio, "imperative_ratio": imperative_ratio},
                "stance": {"hedging_ratio": hedging_ratio, "assertion_ratio": assertion_ratio, "self_reference_ratio": self_reference_ratio},
                "punct_emoji": punct_emoji,
                "code_switching": code_switching,
                "signature_metaphors": signature_metaphors,
                "negative_openers": negative_openers,
            }
        except Exception:
            style_dna_obj = {}

        try:
            # Core tensions simple lexical heuristics
            def _score(tokens: list[str], kws: set[str]) -> float:
                return sum(1 for t in tokens if any(k in t for k in kws)) / max(len(tokens), 1)
            toks = [t.lower() for lst in tokens_lists for t in lst]
            stabi = {"стабил","процесс","порядок","ритм","routine","process","stable"}
            trans = {"кризис","перелом","трансформ","нов","смена","change","pivot","transform"}
            order = {"структур","процесс","окр","kpi","метрик","framework","system"}
            openx = {"интуи","смысл","хаос","креатив","openness","intuition","vibe"}
            dom = {"давлю","жму","жестко","прав","надо","must","should"}
            comm = {"вместе","мы","команда","support","care"}
            vuln = {"боль","страх","стыд","вина","уязвим","vulnerable","shame","fear"}
            analy = {"логик","данн","цифр","факт","метрик","логика","data","metrics","facts"}
            axes: list[dict[str, Any]] = []
            def _axis(name: str, a_kw: set[str], b_kw: set[str]) -> dict[str, Any]:
                a = _score(toks, a_kw); b = _score(toks, b_kw)
                w = round(min(1.0, (a + b) * 0.8), 2)
                # pick up to 2 evidence snippets
                ev = []
                for s in (cleaned[:200] if cleaned else [])[:50]:
                    ls = s.lower()
                    if any(k in ls for k in a_kw.union(b_kw)):
                        ev.append(s[:160])
                        if len(ev) >= 2:
                            break
                return {"name": name, "weight": w, "evidence": ev}
            axes.append(_axis("stability_vs_transformation", stabi, trans))
            axes.append(_axis("order_vs_openness", order, openx))
            axes.append(_axis("dominance_vs_communion", dom, comm))
            axes.append(_axis("analysis_vs_vulnerability", analy, vuln))
            core_tensions_obj = {"axes": axes[:4]}
        except Exception:
            core_tensions_obj = {"axes": []}

        # Merge Digital Twin config into prompt as control hints (lightweight)
        try:
            ai_profile = await ai_profile_repo.get_ai_profile_by_user(user_id)
        except Exception:
            ai_profile = None
        dt_cfg = {}
        try:
            vp = getattr(ai_profile, 'vibe_profile_json', {}) or {}
            dt_cfg = dict(DEFAULT_DT_CONFIG)
            user_dt = vp.get('dt_config') or {}
            if isinstance(user_dt, dict):
                # shallow merge
                for k, v in user_dt.items():
                    dt_cfg[k] = v
        except Exception:
            dt_cfg = DEFAULT_DT_CONFIG

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
        - DO NOT include generic fillers as signature phrases or phrase_weights. Ban list: ["Погнали","Давай сделаем","Круто","Интересно","Поехали","Let's go","Cool","Nice"]. If they occur in data, exclude them.

        PRECOMPUTED_STATS (use anchors and env_quadrant_map; prefer multi-word topics; ignore generic tokens like 'завтра','сколько'):
        {json.dumps(precomputed_stats, ensure_ascii=False)}

        DT_CONFIG (controls for generation in downstream tasks):
        {json.dumps(dt_cfg, ensure_ascii=False)}

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

        # First attempt: normal call (guard against exceptions so `response` is always defined)
        response: Dict[str, Any] | None = None
        try:
            # First attempt with modest token cap to reduce flake
            response = await gemini_service.generate_content(
                prompt,
                overrides={
                    **ai_overrides,
                    "temperature": 0.6,
                    "max_output_tokens": 768,
                    "provider": "proxy" if settings.GEMINI_BASE_URL else None,
                },
            )
        except Exception as call_err:
            response = {"success": False, "error": str(call_err)}
        if not response or not response.get("success"):
            # Fallback immediately without emitting a hard failure to UI
            err_msg = (response or {}).get("error", "LLM analysis failed.")
            logger.error(f"LLM analysis failed for user {user_id}: {err_msg}")
            await notify("llm_failed", error=err_msg)
            try:
                # Choose default profile language based on recent messages
                try:
                    dom_lang = "ru" if precomputed_stats.get("language_distribution", {}).get("ru_cyrillic", 0) > 0.5 else "en"
                except Exception:
                    dom_lang = "en"
                default_profile = _build_default_vibe_profile(dom_lang)
                ai_profile_local = await ai_profile_repo.get_ai_profile_by_user(user_id)
                if not ai_profile_local:
                    ai_profile_local = await ai_profile_repo.create_ai_profile(user_id=user_id)
                # Persist and mark OUTDATED
                await ai_profile_repo.update_ai_profile(
                    ai_profile_local.id,
                    vibe_profile_json=default_profile,
                    analysis_status=AnalysisStatus.OUTDATED,
                    last_analyzed_at=__import__('datetime').datetime.utcnow(),
                    messages_analyzed_count=str(0),
                )
                await websocket_service.send_user_notification(user_id, "vibe_profile_completed", {"profile": default_profile})
                await notify("done", status="OUTDATED")
            except Exception:
                await websocket_service.send_user_notification(user_id, "vibe_profile_warning", {"warning": err_msg})
            return

        content = (response.get("content") or "").strip()
        # Normalize any trailing commas immediately to reduce parsing failures
        content = re.sub(r",\s*([}\]])", r"\1", content)
        await notify("llm_response_received", content_preview=content[:120])
        # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
        if content.startswith("```"):
            try:
                fence_end = content.rfind("```")
                inner = content[3:fence_end] if fence_end != -1 else content[3:]
                if inner.lower().startswith("json"):
                    inner = inner[4:]  # drop 'json' hint
                content = inner.strip()
            except Exception:
                pass
        # Extract JSON block (prefer fenced block first if present)
        json_str = ""
        try:
            if "{" in content and "}" in content:
                # Greedy from first { to last }
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str = content[start:end+1]
        except Exception:
            json_str = ""
        if not json_str:
            # Retry with slightly lower temperature and tokens & attempt minimal schema slice
            try:
                response2 = await gemini_service.generate_content(prompt, overrides={**ai_overrides, "temperature": 0.35, "max_output_tokens": 640, "provider": "proxy" if settings.GEMINI_BASE_URL else None})
                c2 = (response2.get("content") or "").strip() if response2 and response2.get("success") else ""
                if c2:
                    await notify("llm_response_received_alt", content_preview=c2[:120])
                    content = re.sub(r",\s*([}\]])", r"\1", c2)
                    if "{" in content and "}" in content:
                        s2 = content.find('{'); e2 = content.rfind('}')
                        if s2 != -1 and e2 != -1 and e2 > s2:
                            json_str = content[s2:e2+1]
            except Exception:
                pass
        if not json_str:
            # Attempt to salvage by repair rules and brace balancing
            first_idx = content.find('{')
            if first_idx != -1:
                candidate = content[first_idx:]
                # Strip code fences/smart quotes defensively
                try:
                    candidate = candidate.replace('“', '"').replace('”', '"').replace('’', "'")
                except Exception:
                    pass
                # Ensure object keys are quoted when preceded by { or ,
                try:
                    import re as _re_repair
                    candidate = _re_repair.sub(r'([\{,]\s*)([A-Za-z_][A-Za-z0-9_\-]*)\s*:', r'\1"\2":', candidate)
                    # Insert missing commas between object literals in arrays: '}{' -> '}, {'
                    candidate = _re_repair.sub(r'\}\s*\{', '}, {', candidate)
                    # Remove trailing commas before closing braces/brackets
                    candidate = _re_repair.sub(r',\s*([}\]])', r'\1', candidate)
                    # Collapse double commas
                    candidate = _re_repair.sub(r',\s*,+', ',', candidate)
                except Exception:
                    pass
                # Balance braces
                open_curly = candidate.count('{')
                close_curly = candidate.count('}')
                open_square = candidate.count('[')
                close_square = candidate.count(']')
                candidate += '}' * max(0, open_curly - close_curly)
                candidate += ']' * max(0, open_square - close_square)
                try:
                    json.loads(candidate)
                    json_str = candidate
                except Exception:
                    json_str = ""
        if not json_str:
            # Fieldwise extraction attempt: ask LLM for small, strict JSON chunks and merge
            try:
                async def _ask_small_json(prompt_text: str) -> Dict[str, Any]:
                    r = await gemini_service.generate_content(prompt_text, overrides={**ai_overrides, "temperature": 0.3, "max_output_tokens": 384, "provider": "proxy" if settings.GEMINI_BASE_URL else None})
                    c = (r.get("content") or "").strip() if r and r.get("success") else ""
                    if not c:
                        return {}
                    # Strip code fences and trailing commas
                    if c.startswith("```"):
                        fe = c.rfind("```")
                        inner = c[3:fe] if fe != -1 else c[3:]
                        if inner.lower().startswith("json"):
                            inner = inner[4:]
                        c = inner.strip()
                    import re as _re_small
                    c = _re_small.sub(r",\s*([}\]])", r"\1", c)
                    try:
                        return json.loads(c)
                    except Exception:
                        # try greedy braces
                        s = c.find('{'); e = c.rfind('}')
                        if s != -1 and e != -1 and e > s:
                            cc = c[s:e+1]
                            try:
                                return json.loads(cc)
                            except Exception:
                                return {}
                        return {}

                base_ctx = (
                    f"SAMPLE_MESSAGES_START\n{sample_blob[:15000]}\nSAMPLE_MESSAGES_END\n\n"
                    f"PRECOMPUTED_STATS:\n{json.dumps(precomputed_stats, ensure_ascii=False)}\n"
                )
                p1 = (
                    "Infer tone, verbosity, and emoji_usage from the context above.\n"
                    "Return ONLY this JSON object with double-quoted keys/strings and no trailing commas:\n"
                    "{\n  \"tone\": string,\n  \"verbosity\": string,\n  \"emoji_usage\": string\n}"
                )
                j1 = await _ask_small_json(base_ctx + "\n" + p1)

                p2 = (
                    "Extract up to 8 signature phrases you actually use, with integer counts from messages.\n"
                    "Return JSON: {\"signature_phrases\":[{\"text\":string,\"count\":number}]}\n"
                    "Use only double quotes, no trailing commas."
                )
                j2 = await _ask_small_json(base_ctx + "\n" + p2)

                p3 = (
                    "Propose top n-grams that reflect your style (no greetings). Return JSON:"
                    " {\"ngrams\":{\"bigrams\":[string],\"trigrams\":[string]}}\n"
                    "Double quotes only; no trailing commas."
                )
                j3 = await _ask_small_json(base_ctx + "\n" + p3)

                p4 = (
                    "List up to 10 topics_of_interest derived from messages (avoid stopwords/brands).\n"
                    "Return JSON: {\"topics_of_interest\":[string]}\n"
                    "Double quotes only; no trailing commas."
                )
                j4 = await _ask_small_json(base_ctx + "\n" + p4)

                # Build vibe_profile from chunks + computed markers
                vibe_profile = {
                    "tone": j1.get("tone") or "",
                    "verbosity": j1.get("verbosity") or "",
                    "emoji_usage": j1.get("emoji_usage") or "",
                    "signature_phrases": j2.get("signature_phrases") or [],
                    "ngrams": j3.get("ngrams") or {"bigrams": [], "trigrams": []},
                    "topics_of_interest": j4.get("topics_of_interest") or [],
                    "topic_weights": {},
                    "phrase_weights": {},
                }
                # Attach style markers and language distribution from stats
                vibe_profile["style_markers"] = {
                    "emoji_ratio": emoji_ratio,
                    "caps_ratio": caps_ratio,
                    "avg_sentence_len_words": avg_sentence_len_words,
                    "sentence_types": sentence_types,
                    "punctuation": precomputed_stats.get("punctuation", {}),
                    "language_distribution": precomputed_stats.get("language_distribution", {}),
                }
                # Digital comm (minimal)
                endings_sorted = sorted(endings.items(), key=lambda x: x[1], reverse=True)
                vibe_profile["digital_comm"] = {"addressing_style": "ты", "typical_endings": [k for k,_ in endings_sorted[:2]]}
                # Remove greetings/temps if present
                vibe_profile.pop("signature_templates", None)
                # Attach style_dna and core_tensions
                if style_dna_obj:
                    vibe_profile["style_dna"] = style_dna_obj
                if core_tensions_obj:
                    vibe_profile["core_tensions"] = core_tensions_obj

                # Persist fieldwise result
                ai_profile_local = await ai_profile_repo.get_ai_profile_by_user(user_id)
                if not ai_profile_local:
                    ai_profile_local = await ai_profile_repo.create_ai_profile(user_id=user_id)
                await ai_profile_repo.mark_analysis_completed(
                    profile_id=ai_profile_local.id,
                    vibe_profile=vibe_profile,
                    messages_count=len(user_sent_messages),
                )
                await websocket_service.send_user_notification(user_id, "vibe_profile_completed", {"profile": vibe_profile})
                await notify("done", status="FIELDWISE")
                return
            except Exception:
                pass

            # As a last resort, synthesize a profile from precomputed_stats instead of failing hard
            msg = "LLM did not return a JSON block"
            logger.error(f"{msg} for user {user_id}: {content[:200]}")
            await notify("llm_parse_failed")
            # Build minimal profile from stats
            try:
                dom_lang = "ru" if precomputed_stats.get("language_distribution", {}).get("ru_cyrillic", 0) > 0.5 else "en"
            except Exception:
                dom_lang = "en"
            vibe_profile = _build_default_vibe_profile(dom_lang)
            # Merge topics with filtering, n-gram preference, and recency weighting before persisting
            try:
                manual_topics = []
                urepo = container.resolve(UserRepository)
                u = await urepo.get_user(user_id)
                if getattr(u, 'persona_interests_json', None) and isinstance(u.persona_interests_json, list):
                    manual_topics = [str(x) for x in u.persona_interests_json if x]
                mined_uni = precomputed_stats.get("top_unigrams", [])[:100]
                mined_bi = precomputed_stats.get("top_bigrams", [])[:60]
                mined_tri = precomputed_stats.get("top_trigrams", [])[:40]
                channel_hints = precomputed_stats.get("channel_topic_hints", [])
                from collections import Counter as _CtrTopics
                counter = _CtrTopics()
                import re as _re_topic, math as _m
                # Stoplists and noise filters
                stop_ru = {"и","в","на","не","что","это","с","как","я","а","то","у","но","же","к","за","если","по","или","из","для","о","от","до","бы","да","ну","про","так","там","тут","чтобы","при","без","быть","есть","тот","эта","этот","только","уже","ещё","еще","где","когда","всё","все","мы","вы","они","он","она","оно","чем","ли","лишь","вот","такой","такая","такие","мой","моя","мои","твой","твоя","твои","их","наш","ваш","его","ее","её","ничего","чего","кто","что","года","лет","день","раз","сам","сама","само","самые","самый","либо","ни","—","-","мне","меня","мной","нам","нами","вам","вами","тебе","тобой","тебя","ему","ей","ими","всем","себя","очень","просто","тоже","через","если","будет","будут","буду","можно","может","нужно","надо","хочу","хотел","хотела","хотели"}
                stop_en = {"the","and","or","of","to","a","an","in","on","for","with","is","are","be","as","at","by","it","this","that","these","those","we","you","they","i"}
                time_noise_ru = {"сегодня","завтра","вчера","сколько","когда","сейчас","потом","позже","раньше"}
                brand_noise = {"ponchik","чат","channel","club","official","news","тг","чатик","итмо","экс","командой","mindcraft"}
                def is_topic_token(tok: str) -> bool:
                    t = (tok or "").strip().lower()
                    if not t:
                        return False
                    if t in stop_ru or t in stop_en or t in time_noise_ru or t in brand_noise:
                        return False
                    if t == "-":
                        return False
                    if _re_topic.search(r"(юсь|ешь|ешься|ет|ете|ем|ют|ят|ал|ала|али|ишь|ит|им|ите|аю|аешь|ают|ется)$", t):
                        return False
                    if len(t) < 3 and t not in {"ии","ai"}:
                        return False
                    return bool(_re_topic.match(r"^[a-zа-яё-]+$", t))
                def is_good_phrase(phrase: str) -> bool:
                    parts = [p for p in phrase.split() if p]
                    if not parts:
                        return False
                    valid_parts = [pp for pp in parts if is_topic_token(pp)]
                    if len(valid_parts) != len(parts):
                        return False
                    return any(len(pp) >= 4 for pp in parts)
                # Seed with manual/channel/mine signals
                for t in manual_topics or []:
                    if is_topic_token(str(t)):
                        counter[str(t).lower()] += 3
                for t in mined_tri or []:
                    if is_good_phrase(str(t)):
                        counter[str(t).lower()] += 4
                for t in mined_bi or []:
                    if is_good_phrase(str(t)):
                        counter[str(t).lower()] += 3
                for t in mined_uni or []:
                    if is_topic_token(str(t)):
                        counter[str(t).lower()] += 1
                for t in channel_hints or []:
                    if is_topic_token(str(t)):
                        counter[str(t).lower()] += 1
                # Recency-weighted boost from actual messages
                try:
                    from datetime import datetime as _dt
                    now = _dt.utcnow()
                    for m in (user_sent_messages or [])[-600:]:
                        txt = (m.get("text") or "")
                        msg_dt = m.get("date")
                        if not txt or not msg_dt:
                            continue
                        age_days = max((now - msg_dt).days, 0)
                        w = max(0.3, _m.exp(-age_days / 180.0))
                        for tok in _re_topic.findall(r"[A-Za-zА-Яа-яЁё]{3,}", txt):
                            if is_topic_token(tok):
                                counter[tok.lower()] += w
                except Exception:
                    pass
                top_pairs_all = counter.most_common(40)
                # Prefer multi-word phrases first, then allow up to 3 clean unigrams
                phrases = [(k, w) for k, w in top_pairs_all if " " in k]
                unigrams = [(k, w) for k, w in top_pairs_all if " " not in k and is_topic_token(k)]
                selected = phrases[:12] + unigrams[:3]
                if selected:
                    total_w = max(sum(w for _, w in selected), 1)
                    vibe_profile["topics_of_interest"] = [k for k, _ in selected]
                    vibe_profile["topic_weights"] = {k: round(float(w)/float(total_w), 2) for k, w in selected}
                vibe_profile.pop("signature_templates", None)
                # Attach style_dna and core_tensions
                if style_dna_obj:
                    vibe_profile["style_dna"] = style_dna_obj
                if core_tensions_obj:
                    vibe_profile["core_tensions"] = core_tensions_obj
            except Exception:
                pass
            ai_profile = await ai_profile_repo.get_ai_profile_by_user(user_id)
            if not ai_profile:
                ai_profile = await ai_profile_repo.create_ai_profile(user_id=user_id)
            # Do not overwrite existing good profile fields; mark OUTDATED for re-run
            try:
                existing = getattr(ai_profile, "vibe_profile_json", {}) or {}
            except Exception:
                existing = {}
            merged = existing if isinstance(existing, dict) else {}
            # Merge only missing keys
            for k, v in vibe_profile.items():
                merged.setdefault(k, v)
            await ai_profile_repo.update_ai_profile(ai_profile.id, vibe_profile_json=merged)
            try:
                from app.models.ai_profile import AnalysisStatus
                await ai_profile_repo.update_ai_profile(ai_profile.id, analysis_status=AnalysisStatus.OUTDATED)
            except Exception:
                pass
            await websocket_service.send_user_notification(user_id, "vibe_profile_completed", {"profile": vibe_profile})
            await notify("done")
            return
        # Sanitize common issues: trailing commas, smart quotes; fallback to fieldwise if still failing
        try:
            import re as _re_fix
            # Remove any code fences again inside the extracted block
            if json_str.startswith("```"):
                fence_end = json_str.rfind("```")
                inner = json_str[3:fence_end] if fence_end != -1 else json_str[3:]
                if inner.lower().startswith("json"):
                    inner = inner[4:]
                json_str = inner.strip()
            # Strip trailing commas
            json_str = _re_fix.sub(r",\s*([}\]])", r"\1", json_str)
            # Quote unquoted keys at object boundaries
            json_str = _re_fix.sub(r"([\{,]\s*)([A-Za-z_][A-Za-z0-9_\-]*)\s*:", r"\1""\2"":", json_str)
            # Insert missing commas between adjacent object literals
            json_str = _re_fix.sub(r"}\s*{", "}, {", json_str)
            # Collapse accidental double commas
            json_str = _re_fix.sub(r",\s*,+", ",", json_str)
            # Balance braces/brackets conservatively
            oc, cc = json_str.count('{'), json_str.count('}')
            osq, csq = json_str.count('['), json_str.count(']')
            if oc > cc:
                json_str += '}' * (oc - cc)
            if osq > csq:
                json_str += ']' * (osq - csq)
            json_str = json_str.replace("“", '"').replace("”", '"').replace("’", "'")
            vibe_profile = json.loads(json_str)
        except Exception as e:
            logger.error(f"JSON parse failed for user {user_id}: {e}")
            # Try fieldwise extraction before final synth fallback
            try:
                async def _ask_small_json_fw(p: str) -> dict:
                    r = await gemini_service.generate_content(
                        p,
                        overrides={"temperature": 0.3, "max_output_tokens": 384, "provider": "proxy" if settings.GEMINI_BASE_URL else None},
                    )
                    c = (r.get("content") or "").strip() if r and r.get("success") else ""
                    if not c:
                        return {}
                    if c.startswith("```"):
                        fe = c.rfind("```"); inner = c[3:fe] if fe != -1 else c[3:]
                        if inner.lower().startswith("json"): inner = inner[4:]
                        c = inner.strip()
                    c = _re_fix.sub(r",\s*([}\]])", r"\1", c)
                    try:
                        return json.loads(c)
                    except Exception:
                        s = c.find("{"); e2 = c.rfind("}")
                        if s != -1 and e2 != -1 and e2 > s:
                            try:
                                return json.loads(c[s:e2+1])
                            except Exception:
                                return {}
                        return {}

                base_ctx_fw = (
                    f"SAMPLE_MESSAGES_START\n{sample_blob[:15000]}\nSAMPLE_MESSAGES_END\n\n"
                    f"PRECOMPUTED_STATS:\n{json.dumps(precomputed_stats, ensure_ascii=False)}\n"
                )
                p1 = (
                    "Infer tone, verbosity, and emoji_usage from the context above.\n"
                    "Return ONLY this JSON object with double-quoted keys/strings and no trailing commas:\n"
                    "{\n  \"tone\": string,\n  \"verbosity\": string,\n  \"emoji_usage\": string\n}"
                )
                p2 = (
                    "Extract up to 8 signature phrases you actually use, with integer counts from messages.\n"
                    "Return JSON: {\"signature_phrases\":[{\"text\":string,\"count\":number}]}\n"
                    "Use only double quotes, no trailing commas."
                )
                p3 = (
                    "Propose top n-grams that reflect your style (no greetings). Return JSON: {\"ngrams\":{\"bigrams\":[string],\"trigrams\":[string]}}\n"
                    "Double quotes only; no trailing commas."
                )
                p4 = (
                    "List up to 10 topics_of_interest derived from messages (avoid stopwords/brands).\n"
                    "Return JSON: {\"topics_of_interest\":[string]}\n"
                    "Double quotes only; no trailing commas."
                )
                j1 = await _ask_small_json_fw(base_ctx_fw + "\n" + p1)
                j2 = await _ask_small_json_fw(base_ctx_fw + "\n" + p2)
                j3 = await _ask_small_json_fw(base_ctx_fw + "\n" + p3)
                j4 = await _ask_small_json_fw(base_ctx_fw + "\n" + p4)
                vibe_profile = {
                    "tone": j1.get("tone") or "",
                    "verbosity": j1.get("verbosity") or "",
                    "emoji_usage": j1.get("emoji_usage") or "",
                    "signature_phrases": j2.get("signature_phrases") or [],
                    "ngrams": j3.get("ngrams") or {"bigrams": [], "trigrams": []},
                    "topics_of_interest": j4.get("topics_of_interest") or [],
                    "topic_weights": {},
                    "phrase_weights": {},
                }
                # Attach style markers and computed DNA/tensions if available
                vibe_profile["style_markers"] = {
                    "emoji_ratio": emoji_ratio,
                    "caps_ratio": caps_ratio,
                    "avg_sentence_len_words": avg_sentence_len_words,
                    "sentence_types": sentence_types,
                    "punctuation": precomputed_stats.get("punctuation", {}),
                    "language_distribution": precomputed_stats.get("language_distribution", {}),
                }
                if style_dna_obj:
                    vibe_profile["style_dna"] = style_dna_obj
                if core_tensions_obj:
                    vibe_profile["core_tensions"] = core_tensions_obj
                # Persist
                ai_profile_local = await ai_profile_repo.get_ai_profile_by_user(user_id)
                if not ai_profile_local:
                    ai_profile_local = await ai_profile_repo.create_ai_profile(user_id=user_id)
                await ai_profile_repo.mark_analysis_completed(
                    profile_id=ai_profile_local.id,
                    vibe_profile=vibe_profile,
                    messages_count=len(user_sent_messages),
                )
                await websocket_service.send_user_notification(user_id, "vibe_profile_completed", {"profile": vibe_profile})
                await notify("done", status="FIELDWISE_AFTER_PARSE_FAIL")
                return
            except Exception:
                await notify("llm_parse_failed")
            # FINAL FALLBACK: synthesize from stats and mark OUTDATED instead of hard fail
            try:
                try:
                    dom_lang = "ru" if precomputed_stats.get("language_distribution", {}).get("ru_cyrillic", 0) > 0.5 else "en"
                except Exception:
                    dom_lang = "en"
                vibe_profile = _build_default_vibe_profile(dom_lang)
                # Merge topics with filtering and n-gram preference
                manual_topics = []
                try:
                    urepo = container.resolve(UserRepository)
                    u = await urepo.get_user(user_id)
                    if getattr(u, 'persona_interests_json', None) and isinstance(u.persona_interests_json, list):
                        manual_topics = [str(x) for x in u.persona_interests_json if x]
                except Exception:
                    manual_topics = []
                mined_uni = precomputed_stats.get("top_unigrams", [])[:100]
                mined_bi = precomputed_stats.get("top_bigrams", [])[:60]
                mined_tri = precomputed_stats.get("top_trigrams", [])[:40]
                channel_hints = precomputed_stats.get("channel_topic_hints", [])
                from collections import Counter as _CtrTopics
                counter = _CtrTopics()
                import re as _re_topic
                stop_ru = {"и","в","на","не","что","это","с","как","я","а","то","у","но","же","к","за","если","по","или","из","для","о","от","до","бы","да","ну","про","так","там","тут","чтобы","при","без","быть","есть","тот","эта","этот","только","уже","ещё","еще","где","когда","всё","все","мы","вы","они","он","она","оно","чем","ли","лишь","вот","такой","такая","такие","мой","моя","мои","твой","твоя","твои","их","наш","ваш","его","ее","её","ничего","чего","кто","что","года","лет","день","раз","сам","сама","само","самые","самый","либо","ни","—","-","мне","меня","мной","нам","нами","вам","вами","тебе","тобой","тебя","ему","ей","ими","всем","себя","очень","просто","тоже","через","если","будет","будут","буду","можно","может","нужно","надо","хочу","хотел","хотела","хотели"}
                stop_en = {"the","and","or","of","to","a","an","in","on","for","with","is","are","be","as","at","by","it","this","that","these","those","we","you","they","i"}
                def is_topic_token(tok: str) -> bool:
                    t = (tok or "").strip().lower()
                    if not t:
                        return False
                    if t in stop_ru or t in stop_en:
                        return False
                    if t == "-":
                        return False
                    if _re_topic.search(r"(юсь|ешь|ешься|ет|ете|ем|ют|ят|ал|ала|али|ишь|ит|им|ите|аю|аешь|ают|ется)$", t):
                        return False
                    if len(t) < 3 and t not in {"ии","ai"}:
                        return False
                    return bool(_re_topic.match(r"^[a-zа-яё-]+$", t))
                def is_good_phrase(phrase: str) -> bool:
                    parts = [p for p in phrase.split() if p]
                    if not parts:
                        return False
                    valid_parts = [pp for pp in parts if is_topic_token(pp)]
                    if len(valid_parts) != len(parts):
                        return False
                    return any(len(pp) >= 4 for pp in parts)
                for t in manual_topics or []:
                    if is_topic_token(str(t)):
                        counter[str(t).lower()] += 3
                for t in mined_tri or []:
                    if is_good_phrase(str(t)):
                        counter[str(t).lower()] += 4
                for t in mined_bi or []:
                    if is_good_phrase(str(t)):
                        counter[str(t).lower()] += 3
                for t in mined_uni or []:
                    if is_topic_token(str(t)):
                        counter[str(t).lower()] += 1
                for t in channel_hints or []:
                    if is_topic_token(str(t)):
                        counter[str(t).lower()] += 1
                top_pairs_all = counter.most_common(40)
                noise_uni = {"ponchik","чат","channel","club","official","news","тг","чатик"}
                phrases = [(k, w) for k, w in top_pairs_all if " " in k]
                unigrams = [(k, w) for k, w in top_pairs_all if " " not in k and k not in noise_uni]
                selected = phrases[:12] + unigrams[:5]
                if selected:
                    total_w = max(sum(w for _, w in selected), 1)
                    vibe_profile["topics_of_interest"] = [k for k, _ in selected]
                    vibe_profile["topic_weights"] = {k: round(w/total_w, 2) for k, w in selected}
                vibe_profile.pop("signature_templates", None)
                # Persist fallback profile
                ai_profile_local = await ai_profile_repo.get_ai_profile_by_user(user_id)
                if not ai_profile_local:
                    ai_profile_local = await ai_profile_repo.create_ai_profile(user_id=user_id)
                await ai_profile_repo.mark_analysis_completed(
                    profile_id=ai_profile_local.id,
                    vibe_profile=vibe_profile,
                    messages_count=len(user_sent_messages),
                )
                # Immediately mark as OUTDATED to prompt re-run later, without failing the flow
                await ai_profile_repo.update_ai_profile(ai_profile_local.id, analysis_status=AnalysisStatus.OUTDATED)
                await websocket_service.send_user_notification(user_id, "vibe_profile_completed", {"profile": vibe_profile})
                await notify("done", status="OUTDATED")
                return
            except Exception as e2:
                await websocket_service.send_user_notification(user_id, "vibe_profile_warning", {"warning": str(e)})
                return
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

        # Merge computed signals into final profile before saving
        def _merge_style_markers(dst: Dict[str, Any]) -> None:
            sm = dst.setdefault("style_markers", {})
            sm.setdefault("emoji_ratio", emoji_ratio)
            sm.setdefault("caps_ratio", caps_ratio)
            sm.setdefault("avg_sentence_len_words", avg_sentence_len_words)
            sm.setdefault("sentence_types", sentence_types)
            sm.setdefault("punctuation", precomputed_stats["punctuation"]) \
                if "punctuation" not in sm else None
            sm.setdefault("language_distribution", lang_dist)
        def _merge_digital_comm(dst: Dict[str, Any]) -> None:
            dc = dst.setdefault("digital_comm", {})
            # Intentionally omit greetings/farewells per user preference
            ends_sorted = sorted(endings.items(), key=lambda x: x[1], reverse=True)
            dc.setdefault("typical_endings", [k for k, _ in ends_sorted[:2]])

        _merge_style_markers(vibe_profile)
        _merge_digital_comm(vibe_profile)
        # Explicitly remove greetings/farewells if present
        try:
            if "digital_comm" in vibe_profile:
                vibe_profile["digital_comm"].pop("greetings", None)
                vibe_profile["digital_comm"].pop("farewells", None)
        except Exception:
            pass
        if precomputed_stats.get("channel_topic_hints"):
            # Extend topics_of_interest with channel hints if missing
            toi = vibe_profile.setdefault("topics_of_interest", [])
            for w in precomputed_stats["channel_topic_hints"]:
                if w not in toi and len(toi) < 20:
                    toi.append(w)

        # Merge topics into the in-memory profile dict BEFORE persisting
        try:
            manual_topics = []
            try:
                urepo = container.resolve(UserRepository)
                u = await urepo.get_user(user_id)
                if getattr(u, 'persona_interests_json', None) and isinstance(u.persona_interests_json, list):
                    manual_topics = [str(x) for x in u.persona_interests_json if x]
            except Exception:
                manual_topics = []
            # Build mined topics preferring bi/tri-grams over single tokens
            mined_uni = precomputed_stats.get("top_unigrams", [])[:100]
            mined_bi = precomputed_stats.get("top_bigrams", [])[:60]
            mined_tri = precomputed_stats.get("top_trigrams", [])[:40]
            channel_hints = precomputed_stats.get("channel_topic_hints", [])
            from collections import Counter as _CtrTopics
            counter = _CtrTopics()
            import re as _re_topic
            stop_ru = {
                "и","в","на","не","что","это","с","как","я","а","то","у","но","же","к","за","если","по","или","из","для","о","от","до","бы","да","ну","про","так","там","тут","чтобы","при","без","быть","есть","тот","эта","этот","только","уже","ещё","еще","где","когда","всё","все","мы","вы","они","он","она","оно","чем","ли","же","ну","вот","такой","такая","такие","мой","моя","мои","твой","твоя","твои","их","наш","ваш","его","ее","её","ничего","чего","кто","что","года","лет","день","раз","ещё","сам","сама","само","самые","самый","либо","ни","лишь","же","же","то","—","-"
            }
            stop_en = {"the","and","or","of","to","a","an","in","on","for","with","is","are","be","as","at","by","it","this","that","these","those","we","you","they","i"}
            def is_topic_token(tok: str) -> bool:
                t = (tok or "").strip().lower()
                if not t:
                    return False
                if t in stop_ru or t in stop_en:
                    return False
                if t == "-":
                    return False
                if len(t) < 3 and t not in {"ии","ai"}:
                    return False
                return bool(_re_topic.match(r"^[a-zа-яё-]+$", t))
            def is_good_phrase(phrase: str) -> bool:
                parts = [p for p in phrase.split() if p]
                if not parts:
                    return False
                valid_parts = [pp for pp in parts if is_topic_token(pp)]
                if len(valid_parts) != len(parts):
                    return False
                return any(len(pp) >= 4 for pp in parts)

            for t in manual_topics or []:
                if is_topic_token(str(t)):
                    counter[str(t).lower()] += 3
            for t in mined_tri or []:
                if is_good_phrase(str(t)):
                    counter[str(t).lower()] += 4
            for t in mined_bi or []:
                if is_good_phrase(str(t)):
                    counter[str(t).lower()] += 3
            for t in mined_uni or []:
                if is_topic_token(str(t)):
                    counter[str(t).lower()] += 1
            for t in channel_hints or []:
                if is_topic_token(str(t)):
                    counter[str(t).lower()] += 1
            top_pairs = counter.most_common(20)
            if top_pairs:
                total_w = max(sum(w for _, w in top_pairs), 1)
                vibe_profile["topics_of_interest"] = [k for k, _ in top_pairs]
                vibe_profile["topic_weights"] = {k: round(w/total_w, 2) for k, w in top_pairs}
        except Exception:
            pass

        # Remove template scaffolding if present to avoid templated feel
        try:
            if isinstance(vibe_profile, dict) and "signature_templates" in vibe_profile:
                vibe_profile.pop("signature_templates", None)
        except Exception:
            pass
        # Ensure style_dna/core_tensions attached if LLM response lacked them
        try:
            if style_dna_obj and not isinstance(vibe_profile.get("style_dna"), dict):
                vibe_profile["style_dna"] = style_dna_obj
            if core_tensions_obj and not isinstance(vibe_profile.get("core_tensions"), dict):
                vibe_profile["core_tensions"] = core_tensions_obj
        except Exception:
            pass

        await ai_profile_repo.mark_analysis_completed(
            profile_id=ai_profile.id,
            vibe_profile=vibe_profile,
            messages_count=len(user_sent_messages),
        )
        # Ensure user preferred model is synced to gemini-2.5-pro
        try:
            from app.models.ai_request import AIRequestModel
            await user_repo.update_user(user_id, preferred_ai_model=AIRequestModel.GEMINI_2_5_PRO)
        except Exception:
            pass
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
        # Clear analysis lock
        try:
            if 'redis_service' in locals() and redis_service:
                redis_service.delete(f"analysis:lock:{user_id}")
        except Exception:
            pass


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
    from app.core.config import settings
    user_repo = container.resolve(UserRepository)
    ai_profile_repo = container.resolve(AIProfileRepository)
    draft_repo = container.resolve(DraftCommentRepository)
    feedback_repo = container.resolve(NegativeFeedbackRepository)
    gemini_service = container.resolve(GeminiService)
    langchain_service = container.resolve(LangChainService)
    chat_repo = container.resolve(ChatRepository)
    message_repo = container.resolve(TelegramMessageRepository)
    telegram_service = container.resolve(TelegramService)
    websocket_service = container.resolve(WebSocketService)

    try:
        user = await user_repo.get_user(user_id)
        ai_profile = await ai_profile_repo.get_ai_profile_by_user(user_id)
        if not user:
            raise Exception("User not found.")
        # Ensure AI profile exists in dev to avoid early exit
        if not ai_profile or not getattr(ai_profile, "vibe_profile_json", None):
            try:
                from app.tasks.tasks import seed_ai_profile_dev  # self-import safe
                seed_ai_profile_dev.delay(user_id=user_id)
            except Exception:
                pass
            # Reload after seed (best effort)
            ai_profile = await ai_profile_repo.get_ai_profile_by_user(user_id)

        # Resolve Digital Twin config (merge user overrides over defaults)
        dt_cfg: Dict[str, Any] = DEFAULT_DT_CONFIG
        try:
            vp_local = getattr(ai_profile, "vibe_profile_json", None) or {}
            merged = dict(DEFAULT_DT_CONFIG)
            user_dt = vp_local.get("dt_config") or {}
            if isinstance(user_dt, dict):
                for k, v in user_dt.items():
                    merged[k] = v
            dt_cfg = merged
        except Exception:
            dt_cfg = DEFAULT_DT_CONFIG

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

        # Check post relevance (allow forced generation for regeneration & initial seeding)
        force_generate: bool = bool(post_data.get("force_generate", False))
        vibe_profile = ai_profile.vibe_profile_json
        raw_topics = vibe_profile.get("topics_of_interest") or []
        # Defensive normalize to avoid NoneType errors
        norm_topics: list[str] = []
        for t in raw_topics:
            try:
                if t is None:
                    continue
                if isinstance(t, str):
                    tt = t.strip()
                    if tt:
                        norm_topics.append(tt.lower())
                else:
                    norm_topics.append(str(t).lower())
            except Exception:
                continue
        post_text = (post_data.get("original_post_content") or "").lower()
        is_relevant = any(topic in post_text for topic in norm_topics)
        if not norm_topics:
            is_relevant = True

        if not (is_relevant or force_generate):
            logger.info(
                f"Post not relevant for user {user_id}. Skipping draft generation."
            )
            return

        # Construct prompt with local retrieval: fetch up to two short prior posted comments (local tf-idf cosine)
        nearest_snippets: list[str] = []
        try:
            # Build minimal corpus from user's posted comments (DB), cached in Redis
            corpus_key = f"style:corpus:{user_id}"
            corpus: list[str] = []
            cached = container.resolve(RedisService).get(corpus_key)
            if cached and isinstance(cached, list):
                corpus = [c for c in cached if isinstance(c, str)]
            if not corpus:
                posted = await draft_repo.get_recent_posted_by_user(user_id=user_id, limit=200)
                for p in posted:
                    t = (getattr(p, 'final_text_to_post', None) or getattr(p, 'edited_text', None) or getattr(p, 'draft_text', None) or '').strip()
                    if t:
                        corpus.append(t[:160])
                if corpus:
                    container.resolve(RedisService).set(corpus_key, corpus, expire=3600)
            # Local TF-IDF cosine similarity
            import re as _r, math as _m
            pt = (post_data.get('original_post_content') or post_data.get('original_post_text_preview') or '')
            def tokenize(text: str) -> list[str]:
                return [w.lower() for w in _r.findall(r"[A-Za-zА-Яа-яЁё]{3,}", text)]
            docs = [pt] + corpus[:200]
            tokenized = [tokenize(d) for d in docs]
            # Build df
            df: dict[str, int] = {}
            for tokens in tokenized:
                seen = set(tokens)
                for t in seen:
                    df[t] = df.get(t, 0) + 1
            N = len(tokenized)
            def tfidf_vec(tokens: list[str]) -> dict[str, float]:
                tf: dict[str, int] = {}
                for t in tokens:
                    tf[t] = tf.get(t, 0) + 1
                vec: dict[str, float] = {}
                for t, f in tf.items():
                    idf = _m.log((N + 1) / (1 + df.get(t, 1))) + 1.0
                    vec[t] = (f / max(len(tokens), 1)) * idf
                return vec
            vecs = [tfidf_vec(tok) for tok in tokenized]
            def cosine(a: dict[str, float], b: dict[str, float]) -> float:
                dot = sum(a.get(k, 0.0) * v for k, v in b.items())
                na = _m.sqrt(sum(v*v for v in a.values()))
                nb = _m.sqrt(sum(v*v for v in b.values()))
                if na == 0 or nb == 0:
                    return 0.0
                return dot / (na * nb)
            post_vec = vecs[0]
            scored = []
            for idx, c in enumerate(corpus[:200], start=1):
                sim = cosine(post_vec, vecs[idx])
                scored.append((sim, c))
            scored.sort(reverse=True, key=lambda x: x[0])
            for sim, c in scored[:2]:
                if sim > 0:
                    nearest_snippets.append(c)
        except Exception:
            nearest_snippets = []
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
            recent_posted = await draft_repo.get_recent_posted_by_user(user_id=user_id, limit=20)
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
                # Strongly boost explicit style examples (posted via our app)
                curated_boost = 0.6 if isinstance(gp, dict) and gp.get('is_style_example') else 0.0
                # Baseline boost for anything the user actually sent
                posted_boost = 0.25
                weight = min(1.0, recency_w + posted_boost + curated_boost)
                examples_weighted.append(f"- [WEIGHT {weight:.2f}] {text}")
            positive_examples = "\n".join(examples_weighted)
        except Exception:
            positive_examples = ""

        # Compute persona directives once here for downstream usage
        # Avoid referencing local variables before assignment; derive channel title from post_data
        channel_title_hint = None
        try:
            if isinstance(post_data.get('channel'), dict):
                channel_title_hint = post_data.get('channel', {}).get('title')
            if not channel_title_hint:
                channel_title_hint = post_data.get('channel_title')
        except Exception:
            channel_title_hint = None
        persona_directives = _compute_persona_directives(
            post_text=post_data.get('original_post_content') or post_data.get('original_post_text_preview') or '',
            channel_title=channel_title_hint,
            dt_cfg=dt_cfg,
        )

        # Extract anchors from the current post content for grounding and scoring
        import re as _re_anchor
        _post_full = (post_data.get('original_post_content') or post_data.get('original_post_text_preview') or '')
        def _extract_numbers(text: str) -> list[str]:
            return _re_anchor.findall(r"(?<!\w)(?:[0-9][0-9\.,%]*)", text)
        def _extract_quotes(text: str) -> list[str]:
            return [m.group(1) for m in _re_anchor.finditer(r"[«\"\']([^»\"\']{4,120})[»\"\']", text)]
        def _extract_named_entities_simple(text: str) -> list[str]:
            return [
                _re_anchor.sub(r"\s+", " ", m.group(0)).strip()
                for m in _re_anchor.finditer(r"(?:\b[А-ЯЁ][а-яё]+\b(?:\s+|\-)){1,3}\b[А-ЯЁ][а-яё]+\b", text)
            ]
        anchors_post = {
            "numbers": _extract_numbers(_post_full)[:20],
            "quotes": _extract_quotes(_post_full)[:10],
            "entities": _extract_named_entities_simple(_post_full)[:20],
        }

        prompt = f"""
        You are an AI assistant generating a Telegram comment for a user.
        USER VIBE PROFILE: {json.dumps(ai_profile.vibe_profile_json, indent=2)}
        DT_CONFIG: {json.dumps(dt_cfg, indent=2, ensure_ascii=False)}
        PERSONA_DIRECTIVES: {json.dumps(persona_directives, indent=2, ensure_ascii=False)}
        POST TO COMMENT ON: {post_data.get('original_post_content')}
        PRIOR_USER_COMMENTS (style hints, <=160 chars each): {nearest_snippets or 'None'}
        CHANNEL CONTEXT (recent messages):
        {channel_context}
        
        USER'S PAST REJECTIONS (learn from these mistakes):
        {feedback_context if feedback_context else "None"}

        USER'S PAST APPROVED/POSTED EXAMPLES (imitate this vibe):
        {positive_examples if positive_examples else "None"}

        INSTRUCTIONS:
        - Adhere to PERSONA_DIRECTIVES:
          - Archetype mode ← {persona_directives.get('archetype_mode')}
          - Environment quadrant ← {persona_directives.get('environment_quadrant')}
          - HD filter ← {persona_directives.get('hd_filter')} with authority {persona_directives.get('authority')}
          - Trauma mode (if set) ← {persona_directives.get('trauma_mode')}
          - Sub-persona (if set) ← {persona_directives.get('sub_persona')} (apply style_mod if provided)
        - If trauma_mode is set, prioritize its lexicon/behavior and keep the comment concise.
        - Enforce anchors: cite at least one concrete claim/number/named entity from the post.
        - Match the user's vibe PERFECTLY (tone, brevity, emoji level). Use their typical endings if natural.
        - Avoid generic starters or filler phrases. Be specific and situated in the post.
        - Output ONLY the comment text. No quotes, no markdown.
        - If environment is LOW_SAFE_LOW_DEPTH and no concrete anchor can be cited confidently, return exactly: __SKIP__
        """

        # Generate comment (K candidates + rerank)
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

        candidates: list[tuple[str, float]] = []
        k = int((dt_cfg.get("generation_controls") or {}).get("num_candidates", 1))
        k = max(1, min(k, 3))
        for i in range(k):
            resp = await gemini_service.generate_content(prompt, overrides={**ai_overrides, "provider": "proxy" if settings.GEMINI_BASE_URL else None})
            draft = (resp.get("content") or "").strip() if resp and resp.get("success") else ""
            if not draft:
                continue
            # Post-process
            draft = _strip_generic_openers(draft, dt_cfg)
            # Scoring: style match + persona congruence + anchor presence + env appropriateness
            score = 0.0
            # Anchor presence: entities or numeric patterns from the post appear in the draft
            has_anchor = False
            try:
                dl = draft.lower()
                for ent in anchors_post.get('entities', [])[:5]:
                    if ent and ent.lower() in dl:
                        has_anchor = True
                        break
                if not has_anchor:
                    nums = anchors_post.get('numbers', [])[:5]
                    if nums:
                        draft_digits = _re_anchor.findall(r"[0-9]+", draft)
                        draft_digits_blob = " ".join(draft_digits)
                        for num in nums:
                            n_digits = "".join(_re_anchor.findall(r"[0-9]+", num))
                            if n_digits and n_digits in draft_digits_blob:
                                has_anchor = True
                                break
            except Exception:
                has_anchor = False
            score += 0.3 if has_anchor else 0.0
            # Question ratio preference
            want_q = (dt_cfg.get("generation_controls",{}).get("rhetoric",{}).get("question_ratio_target",0.6) or 0.0)
            is_q = 1.0 if draft.strip().endswith('?') else 0.0
            score += 0.2 * (1.0 - abs(want_q - is_q))
            # Length window
            min_len, max_len = (dt_cfg.get("generation_controls",{}).get("length",{}).get("char_target", [80,180]) or [80,180])
            L = len(draft)
            if min_len <= L <= max_len:
                score += 0.2
            # Environment appropriateness
            env = persona_directives.get('environment_quadrant')
            if env == 'LOW_SAFE_HIGH_DEPTH' and '!' not in draft:
                score += 0.1
            if env == 'LOW_SAFE_LOW_DEPTH' and draft == '__SKIP__':
                score += 0.3
            candidates.append((draft, score))

        if not candidates:
            return
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_text = candidates[0][0]
        if best_text == '__SKIP__':
            logger.info(f"Skipping draft due to toxic/low-depth environment for user {user_id}")
            return

        # Call LLM with protective try/except so we can fallback on failures
        try:
            response = await gemini_service.generate_content(prompt, overrides={**ai_overrides, "provider": "proxy" if settings.GEMINI_BASE_URL else None})
        except Exception as e:
            # Normalize into response dict so the fallback below can trigger
            response = {"success": False, "error": str(e)}
        error_text = str(response.get("error", "")) if isinstance(response, dict) else ""
        content_text: str = ""
        if response and response.get("success"):
            content_text = (response.get("content") or "").strip()

        # Graceful degrade: if any failure OR empty content, still create a minimal draft so feed stays useful
        if (not response or not response.get("success")) or not content_text:
            # Distinct fallback so the user sees change after regeneration
            if rejected_draft_id:
                variations = [
                    "Окей, возьму другой угол. По сути — коротко и по делу.",
                    "Попробую иначе: компактно и ближе к сути.",
                    "Скажу по‑другому: лаконично, без воды.",
                ]
                draft_text = random.choice(variations)
            else:
                draft_text = (
                    "Круто. Вижу тему, которая мне близка. Подписываюсь на апдейт. "
                    "(AI временно ограничен/недоступен, поэтому коротко.)"
                )
        else:
            draft_text = content_text
        # Unwrap accidental JSON objects like {"comment": "..."}
        try:
            if isinstance(draft_text, str) and draft_text.strip().startswith('{'):
                parsed = json.loads(draft_text)
                if isinstance(parsed, dict):
                    for key in ("comment", "text", "reply", "message"):
                        if isinstance(parsed.get(key), str) and parsed.get(key).strip():
                            draft_text = parsed.get(key).strip()
                            break
        except Exception:
            pass

        # Enforce anti-generic controls: strip emoji/symbol-only starters
        try:
            lang_hint = "ru"
            try:
                vp = ai_profile.vibe_profile_json or {}
                lang_hint = (vp.get("dominant_language") or "ru")
            except Exception:
                pass
            banned_starters = []
            try:
                dt_cfg_local = dt_cfg if isinstance(dt_cfg, dict) else {}
                lex = (dt_cfg_local.get("persona", {}).get("voice", {}).get("lexicon", {}) if dt_cfg_local else {})
                # Explicitly do NOT include greetings like "йо", "привет", "yo" (they are not desired greetings to be auto-added)
                banned_starters = list(set((dt_cfg_local.get("anti_generic", {}).get("stop_phrases", []) or []) + (lex.get("banned_starters", []) or [])))
            except Exception:
                banned_starters = []
            draft_text = _strip_generic_openers(
                draft_text,
                original_post=post_data.get("original_post_content"),
                lang=lang_hint,
                banned_starters=banned_starters,
            )
        except Exception:
            pass

        # Ensure we have a DB message id; resolve or create using channel_telegram_id + post_telegram_id
        gen_params: Dict[str, Any] = {}
        try:
            if channel_telegram_id and db_chat:
                gen_params["channel_title"] = getattr(db_chat, "title", None)
                gen_params["channel_telegram_id"] = int(channel_telegram_id)
            elif isinstance(post_data.get("channel"), dict):
                gen_params["channel_title"] = post_data.get("channel", {}).get("title")
                if post_data.get("channel", {}).get("id"):
                    gen_params["channel_telegram_id"] = int(post_data.get("channel", {}).get("id"))

            post_tg_id = None
            if post_data.get("original_message_telegram_id") and str(post_data.get("original_message_telegram_id")).isdigit():
                post_tg_id = int(post_data.get("original_message_telegram_id"))
                gen_params["post_telegram_id"] = post_tg_id

            db_msg_id = post_data.get("original_message_id")
            db_message = None
            if db_msg_id and str(db_msg_id).isdigit():
                db_message = await message_repo.get_message(str(db_msg_id))
            elif db_chat and post_tg_id is not None:
                # Try to find/create by chat and telegram id
                db_message = await message_repo.get_message_by_chat_and_telegram_id(db_chat.id, post_tg_id)
                if not db_message:
                    # Create minimal message row
                    created_list = await message_repo.create_or_update_messages(
                        [
                            TelegramMessengerMessage(
                                telegram_id=post_tg_id,
                                chat_id=db_chat.id,
                                text=post_data.get("original_post_content") or "",
                                date=telegram_service._convert_to_naive_utc(__import__('datetime').datetime.utcnow()),
                            )
                        ]
                    )
                    db_message = created_list[0] if created_list else None
            if db_message:
                post_data["original_message_id"] = str(db_message.id)
        except Exception:
            pass

        # Resolve and align model tag to Gemini if user pref is missing or non-Gemini
        model_used = str(getattr(getattr(user, "preferred_ai_model", None), "value", "") or "")
        if "gemini" not in model_used:
            try:
                from app.models.ai_request import AIRequestModel
                updated_user = await user_repo.update_user(user_id, preferred_ai_model=AIRequestModel.GEMINI_2_5_PRO)
                if updated_user and getattr(updated_user, "preferred_ai_model", None):
                    model_used = str(updated_user.preferred_ai_model.value)
                else:
                    model_used = "gemini-2.5-pro"
            except Exception:
                model_used = "gemini-2.5-pro"

        draft_create_data = DraftCommentCreate(
            original_message_id=post_data.get("original_message_id", "unknown"),
            user_id=user_id,
            persona_name=ai_profile.persona_name,
            ai_model_used=(model_used or "gemini-2.5-pro"),
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
                        media_type = None
                        media_url = None
                        try:
                            if getattr(message, 'photo', None) is not None:
                                media_type = 'photo'
                                media_path = await telegram_service.download_message_photo(user.id, int(dialog.id), int(message.id))
                                if media_path:
                                    media_url = media_path
                        except Exception:
                            pass

                        db_messages = await message_repo.create_or_update_messages(
                            [
                                TelegramMessengerMessage(
                                    telegram_id=message.id,
                                    chat_id=db_chat.id,
                                    text=message.text,
                                    date=telegram_service._convert_to_naive_utc(message.date),
                                    media_type=media_type,
                                    file_id=media_url,
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
                # Determine correct chat type: broadcast=True => CHANNEL, else SUPERGROUP
                is_broadcast = bool(getattr(dialog.entity, "broadcast", False))
                created_list = await chat_repo.create_or_update_chats(
                    [
                        TelegramMessengerChat(
                            telegram_id=int(dialog.id),
                            user_id=user.id,
                            type=TelegramMessengerChatType.CHANNEL if is_broadcast else TelegramMessengerChatType.SUPERGROUP,
                            title=getattr(dialog.entity, "title", "Unnamed Channel"),
                            comments_enabled=True,
                        )
                    ]
                )
                db_chat = created_list[0] if created_list else None
                if not db_chat:
                    continue

            async for message in client.iter_messages(dialog, limit=per_dialog_messages):
                if not (getattr(message, "text", None) or getattr(message, "photo", None)):
                    continue

                media_type = None
                media_url = None
                try:
                    if getattr(message, 'photo', None) is not None:
                        media_type = 'photo'
                        media_path = await telegram_service.download_message_photo(user.id, int(dialog.id), int(message.id))
                        if media_path:
                            media_url = media_path
                except Exception:
                    pass

                saved = await message_repo.create_or_update_messages(
                    [
                        TelegramMessengerMessage(
                            telegram_id=message.id,
                            chat_id=db_chat.id,
                            text=message.text,
                            date=telegram_service._convert_to_naive_utc(message.date),
                            media_type=media_type,
                            file_id=media_url,
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


# --- Maintenance tasks ---

@celery_app.task(name="tasks.normalize_chat_types_for_user", queue="scheduler")
def normalize_chat_types_for_user(user_id: str):
    """Normalize saved chat types for a user in the background."""
    logger.info("Starting normalize_chat_types_for_user for user_id=%s", user_id)
    asyncio.run(async_normalize_chat_types_for_user(user_id))


async def async_normalize_chat_types_for_user(user_id: str):
    telegram_service = container.resolve(TelegramService)
    chat_repo = container.resolve(ChatRepository)

    client = await telegram_service.get_or_create_client(user_id)
    if not client:
        logger.warning("No Telegram client for user %s; aborting normalize chat types", user_id)
        return

    try:
        saved_chats = await chat_repo.get_user_chats(user_id=user_id, limit=10000, offset=0)
        if not saved_chats:
            return

        from app.models.chat import TelegramMessengerChat, TelegramMessengerChatType
        from telethon.tl.types import Channel as TelethonChannel, Chat as TelethonChat, User as TelethonUser

        updates: list[TelegramMessengerChat] = []
        for chat in saved_chats:
            try:
                entity = await client.get_entity(int(chat.telegram_id))
            except Exception:
                continue

            if isinstance(entity, TelethonChannel):
                is_broadcast = bool(getattr(entity, "broadcast", False))
                new_type = TelegramMessengerChatType.CHANNEL if is_broadcast else TelegramMessengerChatType.SUPERGROUP
            elif isinstance(entity, TelethonChat):
                new_type = TelegramMessengerChatType.GROUP
            elif isinstance(entity, TelethonUser):
                new_type = TelegramMessengerChatType.PRIVATE
            else:
                continue

            if new_type != chat.type:
                updates.append(
                    TelegramMessengerChat(
                        telegram_id=int(chat.telegram_id),
                        user_id=user_id,
                        type=new_type,
                        title=chat.title,
                        member_count=chat.member_count,
                    )
                )

        if updates:
            await chat_repo.create_or_update_chats(updates)
            logger.info("Normalized %s chats for user %s", len(updates), user_id)
    finally:
        await telegram_service.disconnect_client(user_id)