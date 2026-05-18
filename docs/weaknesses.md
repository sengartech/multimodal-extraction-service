# Weaknesses

This document is to know weaknesses in the current implementation. I am intentionally documenting these before the system is fully polished because the extraction layer should be evaluated by how it fails, not only by happy-path output.

## Weakness 1 — Drawing parser is architecturally two-pass but not yet visually intelligent

### Issue

The current drawing parser is explicitly two-pass:

1. first pass produces a `DrawingGeometrySummary`
2. second pass produces `DrawingSemanticInference`

However, the first pass is still a deterministic scaffold for the provided fixture. It does not yet perform real OCR, line detection, scale extraction, symbol recognition, or geometric measurement from the drawing image.

### Why it matters in production

For construction pricing, drawings can carry critical information:

- room dimensions
- wall lengths
- opening widths
- fixture placement
- circulation constraints
- access constraints

If the drawing parser cannot reliably extract dimensions, it should not produce quantity estimates. The current implementation handles this safely by assigning conservative confidence and surfacing must-have clarifying questions, but it does not yet unlock much pricing value from drawings.

### Regression test

A useful regression test would add a drawing fixture with explicit visible dimensions, for example:

- room width = 2.4m
- room length = 3.1m
- opening width = 80cm

Expected behavior:

- `pass_1_extract_geometry()` should return explicit `DrawingDimension` values.
- Each extracted dimension should have `is_explicit=True`.
- The final `ExtractorResult` should not ask for those exact dimensions again.

This test would fail today because the current parser always marks these dimensions as unknown/low confidence.

### What would have prevented it

A small drawing benchmark with explicit dimensions and expected geometry outputs would have forced the first pass to do real OCR/geometry extraction earlier.

---

## Weakness 2 — Text and audio extraction depend on model-client output quality

### Issue

The text extractor is generic and LLM-backed, which is appropriate for messy contractor notes. However, the current extractor trusts the injected `TextModelClient` to return a well-structured `TextExtractionDraft`.

The schema validates types and confidence ranges, but the extractor does not yet deeply validate semantic consistency. For example, a model client could return:

- task references that do not match material `related_task_ids`
- duplicate task IDs
- vague task names
- missing point A / point B detail
- low-quality clarifying questions
- inconsistent quantities

### Why it matters in production

LLM structured output can be valid JSON but still semantically poor. If poor draft output is accepted without checks, the downstream fusion layer may produce a scope that is syntactically valid but not commercially useful.

This matters because pricing depends on task identity, quantities, and unresolved gaps. A valid schema is necessary but not sufficient.

### Regression test

A useful regression test would inject a fake text model client that returns:

- duplicate task IDs
- a material referencing a non-existent task ID
- a task with generic text like “do work”
- no clarifying question despite missing quantities

Expected behavior:

- the extractor or fusion layer should flag these as validation warnings or unresolved conflicts.
- pricing readiness should be blocked if critical references are invalid.

This would fail today because the extractor maps the draft into typed records but does not yet add semantic validation warnings.

### What would have prevented it

A semantic validation layer between extractor output and fusion would have caught structurally valid but low-quality model outputs earlier.

---
