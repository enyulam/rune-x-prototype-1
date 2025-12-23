## Rune-X OCR & Translation Pipeline – Phased Overview

**Scope**: Backend OCR + Dictionary + MarianMT + Qwen + Reading-Order Modernization  
**Context**: Complements existing product-level phases in `PHASES_STATUS.md` and backend detail docs under `services/inference/`.

---

## Phase 3 – CC‑CEDICT OCR Fusion

- **Goal**: Integrate the full CC‑CEDICT dictionary into OCR fusion to improve character selection and meaning coverage.
- **Key Features**:
  - CCDictionary with ~120k entries.
  - IoU‑based fusion of EasyOCR + PaddleOCR.
  - Dictionary‑guided tie‑breaking when OCR engines disagree.
  - Coverage and unmapped‑character metrics.
- **Status**: Complete (with rollback learnings captured in `PHASE3_ROLLBACK_SUMMARY.md`).

---

## Phase 4 – CC‑CEDICT Translation Module

- **Goal**: Replace the legacy `RuleBasedTranslator` with a robust `CCDictionaryTranslator`.
- **Key Features**:
  - Character‑to‑meaning lookup with definition selection strategies.
  - Translation coverage metrics.
  - API response enrichment (`translation_source`, coverage, unmapped).
- **Status**: Complete (`PHASE4_COMPLETE.md`).

---

## Phase 5 – MarianMT Adapter (Semantic Refinement)

- **Goal**: Turn MarianMT from a black‑box “translator” into a constrained **semantic refinement engine**.
- **Key Features**:
  - `MarianAdapter` with structured input/output.
  - Dictionary‑anchored token locking (placeholders).
  - Phrase‑level refinement scaffolding (phrase spans).
  - Semantic confidence metrics and metadata (`semantic` field).
- **Status**: Complete (`PHASE5_SUMMARY.md`, `PHASE5_MARIANMT_REFACTOR.md`).

---

## Phase 6 – Qwen Adapter (LLM Refinement)

- **Goal**: Wrap Qwen2.5‑1.5B in a constrained adapter that refines MarianMT output under strict semantic rules.
- **Key Features**:
  - `QwenAdapter` + `QwenSemanticContract`.
  - English‑side token locking propagated from Chinese glyph locks.
  - Phrase‑level span identification (on English tokens).
  - Qwen semantic confidence metrics and `qwen` metadata in API responses.
  - Full pipeline smoke tests and documentation.
- **Status**: Complete (`PHASE6_SUMMARY.md`, `PHASE_6_COMPLETE.md`, `PHASE_6_EXPLANATION.md`).

---

## Phase 7 – Enhanced Features & UX (Product‑Level)

- **Goal**: Improve the **user experience** around OCR & translation (batch, progress, visualization, export).
- **Key Features** (high level):
  - Batch processing endpoints and UI.
  - Progress indicators and real‑time updates.
  - Image preview with bounding‑box overlays.
  - Confidence visualization and export formats.
- **Status**: Planned / in progress at product layer (`PHASE_7_EXPLANATION.md`).

> Note: Phase 7 is primarily frontend/UX + API surface, while Phases 3–6 are the core backend OCR/translation internals.

---

## How These Phases Relate

- **Phases 3–6 (Backend Core)**: Build a rich OCR + CC‑CEDICT + MarianAdapter + QwenAdapter stack with semantic constraints.
- **Phase 7 (Product UX)**: Exposes these capabilities with better UX (batch, progress, visualization, export).

This file is the **single high‑level map** of the OCR/translation pipeline phases and should be kept in sync as phases are implemented or adjusted.


