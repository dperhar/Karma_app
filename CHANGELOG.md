# Changelog

All notable changes to this project will be documented in this file.

## v1.8 – DT freeform robustness, Gemini proxy hardening, DT-aware analysis prep (2025-08-13)

### Backend
- Freeform compiler: chunked fallback + heuristic compile; preview/apply never hard-fails; richer WS stages.
- Analyzer: stricter JSON repair; fieldwise extraction after parse-fail; synthesized profile only as last resort; no generic caps.
- Draft generation: proxy provider override, safer guards, SKIP preserved; settings imported in function scopes to avoid NameErrors.
- Gemini service: proxy model candidates (gemini-2.0-flash-lite, gemini-pro, 1.5-pro), response_format json_object, relaxed safety; env-driven model prefs and optional fallbacks.
- Config: DT_FREEFORM flags; GEMINI_MODEL_DEV/PROD and GEMINI_ENABLE_FALLBACKS.
- Compose: rely on .env via env_file; avoid overriding GEMINI_* with empty values.

### Frontend
- AI Controls: model list updated (2.5 Pro, 2.0 Flash Lite, 1.5 Pro), provider toggle, fallback toggle (UI-only).
- Digital Twin panel: Freeform panel (preview/apply/rollback), tokens estimate, notes; talents and banned_starters normalized; logs stable.
- Store: modelCapabilities extended.

### Notes
- No DB migrations; JSON-only changes in `vibe_profile_json`.
- Next step: DT-aware alignment/drift metrics and recalibration flow.

---

## v1.4 – Digital Twin upgrade, Gemini hardening, and DT UI overhaul (2025-08-12)

### Highlights
- Full Digital Twin (DT) persona schema encoded and applied via `dt_config`.
- Robust Gemini 2.5 Pro integration for analysis with low-temp retry and safer fallbacks.
- Telegram ingestion: 3-year scan, supergroups support, reply filtering, and in-code `min_date`.
- Draft generation quality boosts: semantic sub‑persona activation, anchors enforcement, retrieval hints, anti‑generic controls.
- Settings UI: modern DT editor with autosave, advanced sliders/toggles, sub‑persona tester, split logs.

### Backend
- DT config & persona directives
  - Added and expanded `DEFAULT_DT_CONFIG` (archetype, values, talents, voice lexicon; dynamic filters for sub‑personas, trauma response, environment; HD/astro).
  - Implemented `_compute_persona_directives` with hybrid semantic activation (TF‑IDF over cues/examples/triggers), FARMER/SHAMAN/SYNTHESIS archetype selection, HD filter and authority, environment quadrant, trauma overrides.
  - Draft prompts now include `DT_CONFIG` and computed `PERSONA_DIRECTIVES`.
  - Post‑processing strips banned generic openers and enforces anchors.

- Telegram service
  - `get_user_sent_messages(user_id, limit, *, min_date, only_replies, include_personal)` API added.
  - Includes supergroups; in‑code `min_date` filter; returns chat metadata (id/title/type) and reply info.
  - Gentle pacing and FloodWait handling.

- Vibe profile analysis (`app/tasks/tasks.py`)
  - Collects and cleans corpus; computes style markers, punctuation, endings, RU/EN mix.
  - Topics extraction improved: trigram/bigram priority; strict stopword/verb filters; brand/noise removal.
  - Gemini 2.5 Pro analysis pipeline via REST with `responseMimeType: application/json`.
  - Hardened JSON handling: code‑fence stripping, brace balancing, and now a second pass at lower temperature.
  - On final LLM failure: synthesize from precomputed stats but DO NOT overwrite good fields; mark profile OUTDATED.
  - WebSocket stages enriched (`llm_response_received`, `llm_response_received_alt`, `llm_parsed_ok`, `persist_start`).

- Retrieval and generation
  - Local TF‑IDF retrieval of user’s posted comments with recency/curation weights; inject top‑2 as style hints.
  - Negative feedback context (last rejections) is injected to avoid repeated mistakes.
  - Channel context fetched from recent messages in the same chat.

- New/updated endpoints
  - `POST /api/v1/users/me/dt-config/load-default` – loads encoded DT personas into user profile.
  - `POST /api/v1/users/me/subpersona-classify-preview` – semantic sub‑persona activation preview for pasted posts.
  - `POST /api/v1/users/me/analyze-context/dry-run` and `/approve` – dry‑run capture and approval (no LLM spend).

### Frontend
- Settings → Digital Twin
  - Always‑on edit mode with debounced autosave.
  - `SubPersonaPanel`: two‑pane UI, add/remove personas, textareas with auto‑resize and soft wrapping, tester that calls preview endpoint and overlays scores on chips.
  - Tag inputs for lexicon/stop‑phrases/anchors types; helpers for nested updates (`ensurePath`).
  - Advanced controls with sliders/toggles/fields for decoding (temperature/top‑p), generation (candidates, length window, question ratio), style metrics (emoji/exclamation limits), anti‑generic toggles.
  - Inline tooltips explaining each control.
  - Logs split into two collapsible sections: “AI Drafts Generation Logs” and “Digital Twin Analysis Logs”.

- UX fixes
  - Import path fix for `SubPersonaPanel`.
  - Textarea wrapping, smarter spacing, compact typography.

### Quality and Safety
- Default ban list for openers enforced; greetings/farewells removed from profile and prompts.
- Outdated/insufficient data guards; fallback no longer overwrites good fields.
- Respectful Telegram timing and error handling.

### Known gaps targeted for next iteration
- Persist enriched per‑message features (anchors/rhetorical_type/env_quadrant/style snapshot) into DB.
- Signatures and phrase weights with recency decay.
- Auto‑reweight persona values and auto‑expand lexicon from mined tokens.
- K‑candidate generation + lightweight reranker + SKIP policy for toxic contexts.
- Edit‑diff learning and nightly rebuild/decay job with drift detection.
- Per‑chat environment overrides UI and mini metrics dashboard.

---

## v1.3 and earlier
- Historical changes omitted here; see previous commits.
