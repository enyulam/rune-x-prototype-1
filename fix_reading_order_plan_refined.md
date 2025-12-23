OCR Alignment Refactor — DP-Based Reading Order & Structure Fix
Phase 1: Foundation & Data Structures (Tasks 1–2)
Task 1: Adapt existing data structures for DP alignment

Goal: Enable DP without breaking downstream consumers (Qwen, Marian, API)

Extend existing OCR character / glyph structures with:

line_id

char_index_in_line

bounding box metadata (already present)

Introduce lightweight DP node:

AlignmentCell(score, prev, action)


🔒 Guardrail:
Do not change glyph IDs or indices used downstream by:

Qwen glyph → token alignment

Phrase spans

Semantic confidence

Task 2: Implement line grouping function

Goal: Replace global reading order with spatially correct lines

Group characters into lines using:

y-overlap

vertical center distance threshold

Preserve left-to-right order inside each line

Output:

List[List[OCRChar]]  # lines


📌 This becomes the only entry point to alignment.

Phase 2: DP Alignment Core Functions (Tasks 3–8)
Task 3–6: Helper functions

iou(box_a, box_b)

lines_overlap(line_a, line_b)

fuse_chars(char_a, char_b)

select_best_option(match, skip_a, skip_b)

💡 These must be:

Pure functions

Deterministic

Side-effect free

Task 7: align_line_chars() (intra-line DP)

Goal: Align OCR engines within a single line

DP over character sequences

Scoring:

Match: +IoU / char similarity

Skip penalty

Backtracking produces aligned char pairs

🧠 Fixes greedy char-level cascades.

Task 8: align_lines() (line-level DP)

Goal: Align entire lines across OCR outputs

DP over lines, using:

line overlap

average char alignment score

Supports:

Missing lines

Inserted lines

🧠 Fixes phrase swaps and block reordering.

Phase 3: Integration (Tasks 9, 12–13)
Task 9: Refactor align_ocr_outputs()

Replace:

Global sort

Two-pointer greedy matching

With:

Line grouping

Line-level DP

Char-level DP per line

🔒 Hard rule:
The output format must remain unchanged to avoid breaking:

MarianAdapter

QwenAdapter

API schema

Task 12–13: Fuse output + pipeline integration

Update fuse_character_candidates() to:

Insert breaks from DP output

Preserve glyph IDs

Run full pipeline smoke test after integration

Phase 4: Paragraph Structure (Tasks 10–11)
Task 10: Gap-based break detection

Inputs:

Line bounding boxes

Vertical gaps

Line alignment confidence

Outputs:

BREAK_LINE

BREAK_PARAGRAPH

Task 11: Insert breaks into fused text

Convert break markers into:

\n

\n\n

Ensure breaks propagate through:

Marian output

Qwen refinement

Token locking

🧠 This is what finally restores paragraph semantics.

Phase 5: Testing & Tuning (Tasks 14–18)
Tests to explicitly include:

Phrase swaps across lines

Paragraph breaks missing in baseline OCR

Mixed single-line + multi-line layouts

Dense text blocks vs sparse layouts

Tuning parameters:

Line overlap threshold

Vertical gap thresholds

DP skip penalties

🔍 Use visual debug dumps where possible.

Phase 6: Documentation & Tests (Tasks 19–21)
Task 19: Unit tests

Line grouping

Intra-line DP

Line-level DP

Break detection

Task 20: Integration tests

Full OCR → API path

Verify:

Glyph order

Break insertion

Qwen alignment still valid

Task 21: Documentation

Architecture diagram:

OCR → Line Grouping → Line DP → Char DP → Break Insertion → Marian → Qwen


Explicitly document:

Why greedy matching was removed

How DP prevents cascading failures

3️⃣ Critical guardrails (do NOT skip these)
🔒 Guardrail 1: Glyph index stability

If glyph indices shift:

Token locking breaks

Qwen confidence becomes meaningless

✅ Always preserve original glyph ordering within logical lines

🔒 Guardrail 2: Break insertion before Qwen

Paragraph breaks must exist before:

Token locking

Phrase span detection

Otherwise phrase spans become semantically wrong.

🔒 Guardrail 3: Smoke tests after each phase

Run:

pytest tests/test_pipeline_smoke.py::test_pipeline_smoke_full -v


After:

Phase 3

Phase 4

Phase 5

This prevents silent regressions.

Final verdict

🟢 Your plan is correct, well-scoped, and mature.
🟢 This is the right next architectural evolution after Phase 6–9.
🟢 You are now fixing layout intelligence, not just OCR accuracy.