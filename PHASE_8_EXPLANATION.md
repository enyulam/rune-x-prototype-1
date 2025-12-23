## Phase 8: Sentence-Scoped Translation Pipeline – Implementation Plan

### 🎯 High-Level Goal

Transform the backend translation flow from:

> OCR → one big Marian call → one Qwen call

into a **coverage-safe, sentence/paragraph-scoped pipeline**:

> OCR → canonical text → segmentation →  
> \[Chinese sentenceᵢ → Marianᵢ → (optional) Qwenᵢ] → ordered recombination

**Key guarantees:**
- Every detected sentence is translated exactly once by Marian.
- Qwen may refine but must **never reduce coverage**.
- No paragraph or sentence disappears silently.
- Every step is inspectable, local, and reversible.

---

## Phase 0 – Canonical Text & Noise Filtering (Precondition)

### 0.1 Canonicalize OCR Text (Before Segmentation)

**Problem**  
`full_text` and glyph-built text can diverge, causing Marian to see content that glyph-based logic never produced.

**Hard rule:**  
Marian input **must** be derived from glyphs whenever there is a mismatch.

**Implementation Steps**
- After OCR fusion, build:
  - `canonical_text = build_text_from_glyphs(glyphs, line_info)`
- Compare `canonical_text` with `full_text`:
  - If mismatch exceeds a small threshold:
    - Log a clear warning.
    - Use `canonical_text` as the input to Marian and downstream segmentation.
  - Keep `full_text` only for debugging / display.

**Outcome:**  
Marian always translates what OCR actually saw (glyph-consistent input).

### 0.2 OCR Watermark / Noise Filtering

**Why**  
Watermarks, page numbers, and stamps can:
- Introduce garbage “sentences”.
- Blow up locked-token counts.
- Increase Qwen hallucination pressure.

**Where**  
Between OCR fusion and segmentation.

**Approaches (OSS-safe)**
- **Region-based filtering**:
  - Ignore fixed corners/margins (e.g., bottom-right watermark region).
- **Pattern filtering**:
  - Strip short, low-information runs (IDs, app tags) that match known patterns.
- **Low-confidence pruning**:
  - Remove glyphs below a very low confidence threshold, especially in marginal regions.

**Rule:**  
Filtering may only **remove** glyphs/text, never alter characters in-place.

---

## Phase 1 – Sentence & Paragraph Segmentation (Chinese Side)

### 1.1 Paragraph Segmentation

**Input:** Canonical Chinese text.  
**Method:**
- Use:
  - Double newlines (if present).
  - Large vertical gaps from Phase-4 geometry (line y-coordinates / gaps).
- Implement:
  - `segment_paragraphs(text: str) -> List[str]`

### 1.2 Sentence Segmentation

**Method:**
- Split within each paragraph on:
  - Chinese punctuation: `。！？!?`
  - Line breaks.
- Implement:
  - `segment_sentences(paragraph: str) -> List[str]`

### 1.3 Stable Segment Structure

Define:

```python
class SegmentedUnit(BaseModel):
    paragraph_index: int
    sentence_index: int
    text: str
```

**Invariant:**  
Ordering is preserved; `(paragraph_index, sentence_index)` is authoritative for recomposition.

---

## Phase 2 – Map Glyphs → Sentences (Alignment Layer)

### 2.1 SentenceSpan Construction

Define:

```python
class SentenceSpan(BaseModel):
    paragraph_index: int
    sentence_index: int
    glyph_indices: List[int]   # global indices into glyph list
    text: str                  # canonical Chinese sentence
```

**Mapping Strategy (robust):**
- **Primary**:
  - Use line grouping and y-order from OCR fusion to determine plausible glyph ranges per sentence.
- **Secondary**:
  - Use sequential glyph concatenation within each line/paragraph to match `SegmentedUnit.text`.
- **Fallback**:
  - If exact matching fails, select the best approximate index range and:
    - Log the decision.
    - Never fail silently.

**Invariant:**  
`glyph_indices` always reference the original `glyphs` array (global index space).

### 2.2 Locking Risk Guard

**Problem**  
Too many locked tokens can push Marian into degenerate behavior or truncation.

**Guard rules:**
- For each `SentenceSpan`:
  - Compute:
    - Sentence length (chars or glyph count).
    - Number of locked tokens.
  - If either exceeds a safe threshold (configurable):
    - **Option A:** Skip placeholder-based locking for that sentence and log:
      - `locking_mode = "disabled_due_to_size"`.
    - **Option B:** Move locking to a future, post-translation alignment strategy.
  - Never blindly lock very large spans of text without guardrails.

---

## Phase 3 – MarianMT Per-Sentence Translation (Coverage Authority)

### 3.1 Sentence-Scoped Marian Calls

**Change**  
Replace the single global MarianAdapter call with per-sentence calls:

```python
marian_outputs = []
for span in sentence_spans:
    out = marian_adapter.translate(
        glyphs=[glyphs[i] for i in span.glyph_indices],
        raw_text=span.text,
        locked_tokens=maybe_locked_tokens_for_span,
        confidence=...,
        dictionary_coverage=...,
    )
    marian_outputs.append((span.paragraph_index, span.sentence_index, out))
```

**Hard guarantees:**
- Every `SentenceSpan` triggers **exactly one** Marian call.
- On failure:
  - Log clearly.
  - Fall back to returning the original Chinese sentence for that slot, **never** an empty string.

### 3.2 Marian Recombination

- Sort `marian_outputs` by `(paragraph_index, sentence_index)`.
- For each paragraph:
  - Join sentence translations (with spaces or `\n` as desired).
- Join paragraphs with `\n\n` to produce:
  - `sentence_translation` (authoritative Marian output).

**Outcome:**  
`sentence_translation` has full sentence/paragraph coverage and becomes the baseline that Qwen cannot undercut.

---

## Phase 4 – Qwen Refinement (Optional, Bounded, Safe)

### 4.1 Scope Choice

Two modes:
- **Option A (recommended initial):** Per-paragraph Qwen refinement.
- **Option B:** Per-sentence Qwen refinement for maximum control and debugging clarity.

### 4.2 Prompt Hardening

Update `_create_refinement_prompt()` to enforce:
- “**Do not omit any sentence.**”
- “**For each input sentence, output exactly one refined sentence.**”
- “If a sentence is already accurate, leave it unchanged.”

**Recommended prompt format (numbered):**

```text
Input:
1. Marian: ...
2. Marian: ...
3. Marian: ...

Output:
1. ...
2. ...
3. ...
```

This allows post-processing to:
- Parse Qwen output by sentence index.
- Detect any dropped or merged sentences immediately.

### 4.3 Qwen Truncation Safety

**Remove** any post-decode hard truncation of the refined text beyond the model’s `max_new_tokens` bound.

If additional safety limits are unavoidable:
- Truncate only at **sentence boundaries**.
- Never cut mid-word or mid-sentence.

**Rationale:**  
Previous mid-sentence truncation was a root cause of paragraph loss in real runs.

### 4.4 Qwen Output Acceptance Policy

For each unit (sentence or paragraph):
- If Qwen output:
  - Has fewer sentences than the input,
  - Cannot be parsed into the expected numbered structure,
  - Or deviates excessively from Marian (by length / structure),
    - **Reject** Qwen output for that unit.
    - Fall back to Marian’s translation for that unit.
    - Mark metadata: `qwen_accepted = False` with a reason code.

---

## Phase 5 – Reassembly & Metadata Preservation

### 5.1 Reassembly

- Preserve original `(paragraph_index, sentence_index)` ordering.
- Join paragraphs with `\n\n`.

**Final outputs:**
- `sentence_translation`: Recombined Marian outputs (coverage authority).
- `refined_translation`: Recombined Qwen outputs (best-effort fluency improvement, per acceptance policy).

### 5.2 Metadata (Debug Gold)

Carry through per span and per paragraph:
- `paragraph_index`
- `sentence_index`
- `glyph_indices`
- Locking decisions (enabled/disabled reasons)
- Qwen:
  - Acceptance / rejection flags
  - Any truncation information

**Goal:**  
Every surprising behavior in the final text can be traced back to a specific:
- Sentence,
- Marian call,
- Qwen call,
- And associated metadata.

---

## Phase 6 – Testing & Smoke Tests (Updated)

### 6.1 Unit Tests

Add/extend tests for:
- Segmentation correctness (paragraphs + sentences).
- Glyph→sentence alignment:
  - `SentenceSpan.glyph_indices` map back to the expected text slices.
- Locking guard behavior:
  - Long sentences or high locked-token counts trigger guarded mode.

### 6.2 Pipeline Smoke Tests

Run smoke tests at key points:

- **After Phase 0**:
  - `canonical_text` is non-empty and consistent with glyphs.

- **After Phase 3**:
  - Marian sentence count == Chinese sentence count.

- **After Phase 4**:
  - Qwen sentence count preserved when Qwen is accepted.

- **Final output**:
  - Paragraph count preserved.
  - Length ratio sanity checks (no catastrophic shrinkage).

### 6.3 Golden Sample – “因为你值得” Page

Assertions:
- All expected paragraphs are present in both:
  - `sentence_translation`
  - `refined_translation` (when Qwen is accepted).
- No paragraph is < 80% of Marian’s own length.
- No sentence disappears silently (per-segment coverage checks).

---

## Final Architectural Outcome

After Phase 8, the backend text pipeline becomes:

- **Marian** = **coverage authority**:
  - Every sentence translated exactly once.
  - Full paragraph structure preserved.
- **Qwen** = **bounded refiner**:
  - Can improve fluency and coherence,
  - But cannot drop or merge sentences unnoticed.
- Sentence/paragraph boundaries are **structural**, not emergent.
- Failures are **local** and observable, not catastrophic.

This is no longer “OCR → translation → hope”, but a **deterministic, inspectable, production-grade pipeline** fully aligned with Rune-X’s long-term semantic and archival goals.


