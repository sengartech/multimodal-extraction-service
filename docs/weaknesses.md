# Weaknesses

I'm writing weaknesses in the current implementation here. I am documenting these because the extraction layer should be judged by how it handles uncertainty, not only by the happy-path final JSON.

## Weakness 1: Drawing extraction is LLM-powered but not benchmarked against measured plans

### Issue

The drawing parser is a real two-pass OpenAI-backed flow:

1. pass 1 extracts geometry-level information into `DrawingGeometrySummary`
2. pass 2 infers construction semantics into `DrawingSemanticInference`

This is better than the earlier deterministic scaffold, but it is still not benchmarked against a labeled set of measured floor plans. The parser can identify visible dimensions and layout clues, but it does not yet prove that those dimensions are pricing-grade.

### Why it matters in production

Construction drawings often contain the quantities that drive price: wall lengths, room dimensions, opening widths, fixture positions, ceiling height, and access constraints.

If the system misreads a handwritten dimension or assigns a number to the wrong wall segment, the downstream price can be wrong. The current implementation handles this safely by treating uncertain drawing dimensions as blockers instead of using them for takeoff, but that also limits automation.

### Regression test

A useful regression test would use a small drawing benchmark with known expected geometry:

- room width = 2.4 m
- room length = 3.1 m
- opening width = 80 cm
- ceiling height = 2.6 m

Expected behavior:

- pass 1 extracts the explicit dimensions with correct labels and units
- pass 2 does not ask clarifying questions for dimensions already extracted confidently
- ambiguous or unitless dimensions are still kept out of pricing-ready quantities

This would likely fail today because the parser is conservative and does not yet have benchmark-driven dimension mapping.

### What would have prevented it

A labeled drawing benchmark created before implementation would have forced the geometry pass to be evaluated on measured outputs instead of only schema validity.

---

## Weakness 2: Structured model outputs are syntactically validated but not deeply semantically validated

### Issue

Text, vision, drawing, and fusion all use structured outputs validated by Pydantic. This catches malformed JSON, wrong enum values, invalid confidence ranges, and missing required fields.

However, the system does not yet perform enough semantic validation across those structured outputs. For example, a model could return:

- duplicate task IDs
- material `related_task_ids` that do not exist
- vague task names like “do work”
- a material quantity with the wrong unit meaning
- a clarifying question that is too generic to unblock pricing
- a task inferred from photo-only evidence without support from text or drawing

### Why it matters in production

Valid JSON is not the same as a valid construction scope.

A downstream pricing engine needs task identity, quantities, units, provenance, and blockers to be commercially meaningful. If semantic issues pass through because the JSON shape is valid, the system can produce a clean-looking but unreliable scope.

### Regression test

A useful regression test would inject fake extractor or fusion outputs with:

- duplicate task IDs
- a material linked to a non-existent task ID
- a task with a generic name
- a photo-only task that is not supported by another modality
- no must-have question despite missing quantity data

Expected behavior:

- the system records validation warnings or unresolved conflicts
- pricing readiness is blocked
- bad task/material references are not silently accepted

This would fail today because the pipeline mostly relies on schema validation and prompt instructions, not a dedicated semantic validation layer.

### What would have prevented it

A semantic validation layer between extraction and fusion, plus tests for invalid-but-well-formed outputs, would have caught these issues earlier.

---

## Weakness 3: Supporting provenance confidence is simplified in the final fused scope

### Issue

The final `ScopeBrief` includes provenance from fusion and supporting captures. However, when supporting capture IDs are attached during fusion, the supporting provenance confidence is currently normalized to `1.0`.

The final fused field confidence is still meaningful, but the supporting evidence confidence does not preserve the original extractor confidence from text, drawing, or vision.

### Why it matters in production

Downstream consumers may need to distinguish between:

- explicit contractor text with high confidence
- uncertain drawing geometry with medium confidence
- blurry or partial photo evidence with lower confidence

If all supporting provenance entries use `1.0`, the source support can look stronger than it actually was, even if the fused field confidence remains conservative.

### Regression test

A useful regression test would create extractor results with different confidence levels:

- text evidence at `0.95`
- drawing evidence at `0.45`
- photo evidence at `0.60`

After fusion, supporting provenance should preserve those original confidence values instead of replacing them with `1.0`.

Expected behavior:

- fusion provenance remains separate
- supporting text provenance keeps high confidence
- supporting drawing/photo provenance keeps lower confidence
- pricing readiness uses the fused confidence and blockers, not inflated source confidence

This would fail today because supporting provenance confidence is simplified.

### What would have prevented it

Passing an evidence index into the fusion mapper would have allowed source capture IDs to resolve back to original extractor-level confidence during provenance attachment.