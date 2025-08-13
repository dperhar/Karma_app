"""API routes for user management."""

import os
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body

from app.dependencies import get_current_user, get_optional_user, logger
from app.schemas.base import APIResponse, MessageResponse
from app.schemas.ai_profile import AIProfileResponse, AIProfileUpdate
from app.schemas.ai_settings import AISettings, AISettingsUpdate
from app.schemas.user import UserResponse, UserUpdate
from app.core.dependencies import container
from app.tasks.tasks import analyze_vibe_profile, capture_context_dry_run, DEFAULT_DT_CONFIG, dt_ingest_freeform, dt_preview_freeform
from app.schemas.context_analysis import ContextApproveRequest
from app.core.config import settings

router = APIRouter()


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_user(
    current_user: Optional[UserResponse] = Depends(get_optional_user),
) -> APIResponse[UserResponse]:
    """Get current user."""
    # Development mode fallback for when auth isn't working
    is_develop = os.getenv("IS_DEVELOP", "true").lower() == "true"
    
    if not current_user and is_develop:
        # Return a mock user for development when authentication fails
        mock_user = UserResponse(
            id="dev-user-123",
            telegram_id=109005276,  # From the frontend logs
            username="dev_user",
            first_name="Development",
            last_name="User", 
            phone_number=None,
            is_active=True
        )
        return APIResponse(
            success=True,
            data=mock_user,
            message="Development mode: mock user returned",
        )
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    return APIResponse(
        success=True,
        data=current_user,
    )


@router.get("/me/ai-profile", response_model=APIResponse[AIProfileResponse])
async def get_my_ai_profile(
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[AIProfileResponse]:
    """Return current user's AI profile (vibe analysis) if exists."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    from app.repositories.ai_profile_repository import AIProfileRepository
    from app.core.dependencies import container

    repo = container.resolve(AIProfileRepository)
    ai_profile = await repo.get_ai_profile_by_user(current_user.id)
    if not ai_profile:
        if settings.IS_DEVELOP:
            ai_profile = await repo.create_ai_profile(user_id=current_user.id)
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI profile not found")

    # Normalize datetime to string for schema compatibility
    payload = AIProfileResponse.model_validate(ai_profile).model_dump()
    if isinstance(payload.get("last_analyzed_at"), (int, float)):
        pass
    return APIResponse(success=True, data=payload)


@router.get("/me/ai-settings", response_model=APIResponse[AISettings])
async def get_my_ai_settings(
    current_user: Optional[UserResponse] = Depends(get_optional_user),
) -> APIResponse[AISettings]:
    """Return current user's AI generation settings (model, temperature, tokens)."""
    # In development, allow returning defaults even if session is not fully established,
    # so the UI can render controls and not show "AI unavailable".
    if not current_user:
        if settings.IS_DEVELOP:
            return APIResponse(success=True, data=AISettings())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    from app.repositories.ai_profile_repository import AIProfileRepository
    repo = container.resolve(AIProfileRepository)
    ai_profile = await repo.get_ai_profile_by_user(current_user.id)
    if not ai_profile:
        # Defaults if no profile yet
        return APIResponse(success=True, data=AISettings())

    # For now, use defaults; can be extended to read persisted values later
    settings_payload = AISettings(
        model="gemini-2.5-pro",
        temperature=0.95,
        max_output_tokens=512,
        provider=(getattr(getattr(ai_profile, "vibe_profile_json", {}), "get", lambda *_: None)("gen_provider") or "google"),
    )
    return APIResponse(success=True, data=settings_payload)


@router.put("/me/ai-settings", response_model=APIResponse[AISettings])
async def update_my_ai_settings(
    settings_update: AISettingsUpdate,
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[AISettings]:
    """Update current user's AI generation settings. Persist on AIProfile for now."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    from app.repositories.ai_profile_repository import AIProfileRepository
    repo = container.resolve(AIProfileRepository)
    ai_profile = await repo.get_ai_profile_by_user(current_user.id)
    if not ai_profile:
        ai_profile = await repo.create_ai_profile(user_id=current_user.id)

    # Persist lightweight generation overrides into vibe_profile_json under 'gen_overrides'
    vp = dict(getattr(ai_profile, "vibe_profile_json", {}) or {})
    gen_overrides = dict(vp.get("gen_overrides", {}) or {})
    if settings_update.model is not None:
        gen_overrides["model"] = settings_update.model
    if settings_update.temperature is not None:
        gen_overrides["temperature"] = settings_update.temperature
    if settings_update.max_output_tokens is not None:
        gen_overrides["max_output_tokens"] = settings_update.max_output_tokens
    if settings_update.provider is not None:
        vp["gen_provider"] = settings_update.provider
    if gen_overrides:
        vp["gen_overrides"] = gen_overrides
        await repo.update_ai_profile(ai_profile.id, vibe_profile_json=vp)

    # Return merged values for immediate UI reflection
    merged = AISettings(
        model=(settings_update.model or gen_overrides.get("model") or "gemini-2.5-pro"),
        temperature=(
            settings_update.temperature
            if settings_update.temperature is not None
            else float(gen_overrides.get("temperature", 0.95))
        ),
        max_output_tokens=(
            settings_update.max_output_tokens
            if settings_update.max_output_tokens is not None
            else int(gen_overrides.get("max_output_tokens", 512))
        ),
        provider=(settings_update.provider or vp.get("gen_provider") or "google"),
    )

    return APIResponse(success=True, data=merged)


@router.put("/me/ai-profile", response_model=APIResponse[AIProfileResponse])
async def update_my_ai_profile(
    profile_update: AIProfileUpdate,
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[AIProfileResponse]:
    """Edit user's Digital Twin: tone, interests, templates, and persona fields.

    Rule: This is synchronous and light. It merges provided fields into the
    existing `vibe_profile_json` and mirrored persona fields, leaving others intact.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    from app.repositories.ai_profile_repository import AIProfileRepository
    repo = container.resolve(AIProfileRepository)
    ai_profile = await repo.get_ai_profile_by_user(current_user.id)
    if not ai_profile:
        ai_profile = await repo.create_ai_profile(user_id=current_user.id)

    # Merge updates into vibe_profile_json
    base = getattr(ai_profile, "vibe_profile_json", {}) or {}
    vp = dict(base)

    def set_if(value, key):
        if value is not None:
            vp[key] = value

    set_if(profile_update.tone, "tone")
    set_if(profile_update.verbosity, "verbosity")
    set_if(profile_update.emoji_usage, "emoji_usage")
    set_if(profile_update.style_prompt, "style_prompt")
    set_if(profile_update.topics_of_interest, "topics_of_interest")
    set_if(profile_update.signature_templates, "signature_templates")
    set_if(profile_update.do_list, "do_list")
    set_if(profile_update.dont_list, "dont_list")

    if profile_update.signature_phrases is not None:
        vp["signature_phrases"] = [
            {"text": t, "count": 1} if isinstance(t, str) else t
            for t in profile_update.signature_phrases
        ]

    # Digital comm subsection
    dc = dict(vp.get("digital_comm", {}) or {})
    if profile_update.greetings is not None:
        dc["greetings"] = profile_update.greetings
    if profile_update.typical_endings is not None:
        dc["typical_endings"] = profile_update.typical_endings
    if dc:
        vp["digital_comm"] = dc

    # Merge dt_config if provided (but do NOT allow editing hd_profile or astro_axis from UI)
    if getattr(profile_update, "dt_config", None):
        try:
            incoming = dict(profile_update.dt_config or {})
            user_dt = dict(vp.get("dt_config", {}) or {})
            # remove forbidden keys
            for forbidden in ("dynamic_filters",):
                if forbidden in incoming:
                    # allow only environment, sub_personalities, trauma_response (shallow)
                    allowed_dyn = {}
                    dyn = incoming.get("dynamic_filters") or {}
                    if isinstance(dyn, dict):
                        if isinstance(dyn.get("sub_personalities"), dict):
                            allowed_dyn["sub_personalities"] = dyn.get("sub_personalities")
                        if isinstance(dyn.get("trauma_response"), dict):
                            allowed_dyn["trauma_response"] = dyn.get("trauma_response")
                        if isinstance(dyn.get("environment"), dict):
                            allowed_dyn["environment"] = dyn.get("environment")
                    incoming.pop("dynamic_filters", None)
                    if allowed_dyn:
                        user_dt["dynamic_filters"] = {**(user_dt.get("dynamic_filters") or {}), **allowed_dyn}
            # merge remaining top-level keys (persona, decoding, generation_controls, anti_generic, style_metrics)
            for k, v in incoming.items():
                if k in {"persona", "decoding", "generation_controls", "anti_generic", "style_metrics"}:
                    user_dt[k] = v
            vp["dt_config"] = user_dt
        except Exception:
            pass

    # Persist back
    updated = await repo.update_ai_profile(
        ai_profile.id,
        vibe_profile_json=vp,
        persona_name=profile_update.persona_name or getattr(ai_profile, "persona_name", None),
        user_system_prompt=profile_update.user_system_prompt or getattr(ai_profile, "user_system_prompt", None),
    )

    return APIResponse(success=True, data=AIProfileResponse.model_validate(updated))


@router.post("/me/dt-config/freeform/preview", response_model=APIResponse[dict])
async def dt_config_freeform_preview(
    body: dict = Body(...),
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[dict]:
    """Queue preview compile of Digital Twin config from freeform text. Does NOT persist.

    Body: { content: str }
    Returns queued status; result will be sent via WS event `dt_freeform_preview` and cached for 10m.
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not settings.DT_FREEFORM_ENABLED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="DT freeform is disabled")

    content = str((body or {}).get("content") or "")
    if not content.strip():
        raise HTTPException(status_code=400, detail="content is required")
    if len(content) > settings.DT_FREEFORM_MAX_CHARS:
        content = content[: settings.DT_FREEFORM_MAX_CHARS]
    try:
        dt_preview_freeform.delay(user_id=current_user.id, content=content)
    except Exception:
        raise HTTPException(status_code=503, detail="queue_unavailable")
    return APIResponse(success=True, data={"status": "queued", "tokens_estimate": min(len(content)//4, 20000)})


@router.post("/me/dt-config/freeform/apply", response_model=APIResponse[dict])
async def dt_config_freeform_apply(
    body: dict = Body(...),
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[dict]:
    """Queue Celery to ingest freeform and persist compiled dt_config with versioning."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not settings.DT_FREEFORM_ENABLED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="DT freeform is disabled")
    content = str((body or {}).get("content") or "")
    apply_mask = (body or {}).get("apply_mask") or {}
    strategy = (body or {}).get("strategy") or "merge"
    if not content.strip():
        raise HTTPException(status_code=400, detail="content is required")
    if len(content) > settings.DT_FREEFORM_MAX_CHARS:
        content = content[: settings.DT_FREEFORM_MAX_CHARS]
    try:
        dt_ingest_freeform.delay(user_id=current_user.id, content=content, apply_mask=apply_mask, strategy=strategy)
    except Exception:
        raise HTTPException(status_code=503, detail="queue_unavailable")
    return APIResponse(success=True, data={"status": "queued"})


@router.get("/me/dt-config/freeform/last", response_model=APIResponse[dict])
async def dt_config_freeform_last(
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[dict]:
    """Return last saved freeform provenance for UI restoration."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    from app.repositories.ai_profile_repository import AIProfileRepository
    repo = container.resolve(AIProfileRepository)
    ai_profile = await repo.get_ai_profile_by_user(current_user.id)
    vp = dict(getattr(ai_profile, "vibe_profile_json", {}) or {}) if ai_profile else {}
    return APIResponse(success=True, data={
        "dt_freeform": vp.get("dt_freeform") or {},
        "dt_config": vp.get("dt_config") or {},
    })


@router.post("/me/dt-config/rollback", response_model=APIResponse[dict])
async def dt_config_rollback(
    body: dict = Body(...),
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[dict]:
    """Rollback dt_config to a previous version id stored in `vibe_profile_json.dt_freeform.versions`.

    Body: { version_id: string }
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    from app.repositories.ai_profile_repository import AIProfileRepository
    repo = container.resolve(AIProfileRepository)
    ai_profile = await repo.get_ai_profile_by_user(current_user.id)
    if not ai_profile or not getattr(ai_profile, "vibe_profile_json", None):
        raise HTTPException(status_code=404, detail="profile_not_found")
    vp = dict(ai_profile.vibe_profile_json or {})
    versions = (vp.get("dt_freeform") or {}).get("versions") or []
    vid = str((body or {}).get("version_id") or "").strip()
    if not vid:
        raise HTTPException(status_code=400, detail="version_id required")
    target = None
    for r in versions:
        if str(r.get("id")) == vid:
            target = r
            break
    if not target or "prev_dt_config" not in target:
        raise HTTPException(status_code=404, detail="version_not_found")
    vp["dt_config"] = target.get("prev_dt_config") or {}
    updated = await repo.update_ai_profile(ai_profile.id, vibe_profile_json=vp)
    return APIResponse(success=True, data={"status": "rolled_back", "version_id": vid, "dt_config": (vp.get("dt_config") or {})})


@router.post("/me/subpersona-classify-preview", response_model=APIResponse[dict])
async def subpersona_classify_preview(
    payload: dict = Body(...),
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[dict]:
    """Preview sub-persona activation using hybrid semantic scoring.

    Body: { post_text: str }
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    from app.repositories.ai_profile_repository import AIProfileRepository
    repo = container.resolve(AIProfileRepository)
    ai_profile = await repo.get_ai_profile_by_user(current_user.id)
    vp = dict(getattr(ai_profile, "vibe_profile_json", {}) or {})
    dt_cfg = dict(vp.get("dt_config", {}) or {})
    text = str(payload.get("post_text") or "")
    def _tokenize(s: str) -> list[str]:
        import re as _r
        return [_r.sub(r"\W+", "", w).lower() for w in _r.findall(r"[A-Za-zА-Яа-яЁё0-9\-]{2,}", s)]
    def _tfidf(tokens_list: list[list[str]]):
        df: dict[str, int] = {}
        for tokens in tokens_list:
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1
        N = max(len(tokens_list), 1)
        vecs: list[dict[str, float]] = []
        import math as _m
        for tokens in tokens_list:
            tf: dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            vec: dict[str, float] = {}
            for t, f in tf.items():
                idf = ((N + 1) / (1 + df.get(t, 0)))
                vec[t] = (f / max(len(tokens), 1)) * (_m.log(idf) + 1.0)
            vecs.append(vec)
        return vecs
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        dot = sum(a.get(k, 0.0) * v for k, v in b.items())
        na = (sum(v*v for v in a.values()) or 0.0) ** 0.5
        nb = (sum(v*v for v in b.values()) or 0.0) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    subs = ((dt_cfg.get("dynamic_filters") or {}).get("sub_personalities") or {})
    if not isinstance(subs, dict) or not text.strip():
        return APIResponse(success=True, data={"persona": None, "score": 0.0, "breakdown": {"semantic": 0.0, "keywords": 0.0}})

    names: list[str] = []
    docs: list[list[str]] = [_tokenize(text)]
    keyword_scores: dict[str, float] = {}
    for name, spec in subs.items():
        spec = spec or {}
        bag = " ".join([str(x) for x in (spec.get("semantic_hints") or []) + (spec.get("examples") or []) + (spec.get("triggers") or []) if isinstance(x, str)])
        docs.append(_tokenize(bag))
        names.append(str(name))
        kw = (spec.get("triggers") or [])
        keyword_scores[str(name)] = 1.0 if any((str(k).lower() in text.lower()) for k in kw) else 0.0
    vecs = _tfidf(docs)
    post_vec = vecs[0]
    best = (None, 0.0, 0.0, 0.0)
    full_scores: dict[str, dict[str, float]] = {}
    for idx, vec in enumerate(vecs[1:]):
        sem = _cosine(post_vec, vec)
        kw = keyword_scores[names[idx]] * 0.1
        score = sem + kw
        full_scores[names[idx]] = {"score": round(score, 3), "semantic": round(sem, 3), "keywords": round(kw, 3)}
        if score > best[1]:
            best = (names[idx], score, sem, kw)
    return APIResponse(success=True, data={"persona": best[0], "score": round(best[1], 3), "breakdown": {"semantic": round(best[2], 3), "keywords": round(best[3], 3)}, "full_scores": full_scores})


@router.put("/me", response_model=APIResponse[UserResponse])
async def update_user(
    user_data: UserUpdate,
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[UserResponse]:
    """Update current user data."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        from app.services.user_service import UserService
        user_service = container.resolve(UserService)
        updated_user = await user_service.update_user(current_user.id, user_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return APIResponse(
            success=True,
            data=updated_user,
            message="User updated successfully",
        )
    except Exception as e:
        logger.error(f"Error updating user: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user",
        ) from e


@router.post("/me/analyze-vibe-profile", response_model=APIResponse[dict])
async def analyze_user_vibe_profile(
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[dict]:
    """
    Trigger analysis of user's Telegram activity to build their vibe profile.
    This is an asynchronous task.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    analyze_vibe_profile.delay(user_id=current_user.id)

    return APIResponse(
        success=True,
        data={"status": "analysis_queued"},
        message="Vibe profile analysis has been queued. You will be notified when it's complete.",
    ) 


@router.post("/me/analyze-context/dry-run", response_model=APIResponse[dict])
async def analyze_user_context_dry_run(
    current_user: Optional[UserResponse] = Depends(get_current_user),
    years: int | None = 3,
    only_replies: bool = False,
    include_personal: bool = False,
    limit: int = 10000,
) -> APIResponse[dict]:
    """Dry-run capture: fetch and cache messages; no LLM spend.

    Returns a run_id and basic metrics so the client can review before approving.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        capture_context_dry_run.delay(
            user_id=current_user.id,
            messages_limit=limit,
            years=years,
            only_replies=only_replies,
            include_personal=include_personal,
        )
    except Exception as _e:
        logger.error(f"Failed to queue dry-run: {_e}")

    return APIResponse(
        success=True,
        data={
            "status": "dry_run_queued",
            "years": years,
            "only_replies": only_replies,
            "include_personal": include_personal,
            "limit": limit,
        },
    )


@router.post("/me/analyze-context/approve", response_model=APIResponse[dict])
async def analyze_user_context_approve(
    body: ContextApproveRequest,
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[dict]:
    """Approve a cached run_id and kick off LLM analysis using the cached set with filters.
    This keeps the API thin; actual selection and LLM call happen in the worker (to be extended).
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    analyze_vibe_profile.delay(user_id=current_user.id, messages_limit=10000)
    return APIResponse(success=True, data={"status": "approved_and_queued", "run_id": body.run_id})
@router.post("/me/analyze-context", response_model=APIResponse[dict])
async def analyze_user_context(
    current_user: Optional[UserResponse] = Depends(get_current_user),
    years: int | None = 3,
    only_replies: bool = False,
    include_personal: bool = False,
) -> APIResponse[dict]:
    """Trigger analysis of user's Telegram activity to build their digital twin context.

    This is an asynchronous task dispatch. The worker will fetch up to 10,000
    of the user's latest sent messages (subject to Telegram API limits and
    internal safety guards) and build/update the user's vibe profile.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    # Dispatch Celery task with a high message limit for deep analysis
    try:
        analyze_vibe_profile.delay(
            user_id=current_user.id,
            messages_limit=10000,
            years=years,
            only_replies=only_replies,
            include_personal=include_personal,
        )
    except Exception:
        # In dev, if Celery is down or no Telegram session, seed a default completed profile
        if settings.IS_DEVELOP:
            from app.tasks.tasks import seed_ai_profile_dev
            seed_ai_profile_dev.delay(user_id=current_user.id)

    return APIResponse(
        success=True,
        data={
            "status": "analysis_queued",
            "years": years,
            "only_replies": only_replies,
            "include_personal": include_personal,
        },
        message=(
            "Context analysis has been queued. We'll analyze up to your latest 10,000 "
            "messages and update your profile when complete."
        ),
    ) 


@router.post("/me/dt-config/load-default", response_model=APIResponse[AIProfileResponse])
async def load_default_dt_config(
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[AIProfileResponse]:
    """Load the full Digital Twin personas (dt_config) into the user's AI profile.

    Synchronous merge: sets `vibe_profile_json.dt_config` = DEFAULT_DT_CONFIG.
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    from app.repositories.ai_profile_repository import AIProfileRepository
    repo = container.resolve(AIProfileRepository)
    ai_profile = await repo.get_ai_profile_by_user(current_user.id)
    if not ai_profile:
        ai_profile = await repo.create_ai_profile(user_id=current_user.id)

    vp = dict(getattr(ai_profile, "vibe_profile_json", {}) or {})
    vp["dt_config"] = DEFAULT_DT_CONFIG

    updated = await repo.update_ai_profile(
        ai_profile.id,
        vibe_profile_json=vp,
        persona_name=getattr(ai_profile, "persona_name", None),
        user_system_prompt=getattr(ai_profile, "user_system_prompt", None),
    )

    return APIResponse(success=True, data=AIProfileResponse.model_validate(updated))