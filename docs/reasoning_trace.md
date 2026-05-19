# Reasoning Trace

As per deliverables, in this document I'm writing the main engineering decisions made while building the scope modeling service. I treated the assignment as a production-shaped extraction problem rather than a one-off script: the system needs to ingest messy contractor inputs, preserve uncertainty, produce typed evidence, and decide whether downstream pricing can safely proceed.

The customer input is intentionally incomplete: a short French note, a hand-drawn floor plan, and five photos. I therefore optimized for traceability, confidence, provenance, and gaps instead of trying to force a fully confident quote from ambiguous inputs.

## 1. Schema-first design

I considered building a narrow schema optimized only for this wine-bar shower job: showers, drain, water heater, placo wall, and utility room. I rejected that because the assignment later asks for schema evolution to support a façade renovation case. A shower-specific schema would look good for the fixture but fail the migration requirement.

I chose a generic but construction-aware `ScopeBrief` model with source captures, tasks, point A / point B, materials, assumptions, exclusions, clarifying questions, provenance, confidence, and pricing readiness.

The most important design choice was making extracted values traceable. A final field like “partition wall height = 2m” is only useful if we know where it came from, which extractor produced it, and how confident the system is. This is why key values use provenance and confidence at field level rather than only at job level.

This decision was influenced by production inventory work I’ve done in logistics. In a 3PL platform, I chose event sourcing for inventory tracking because latest-state values were not enough when something went wrong. We needed to know which inbound, order, return, cancellation, or shipment event caused the final quantity. The same idea applies here: the final scope is less useful without an audit trail of how each field was derived.

## 2. Versioned fields

I considered using plain values like `title: str` and `description: str`. I chose a `VersionedField[T]` shape instead, with value, confidence, provenance, and history.

The reason is that construction scope evolves. The system may initially mark wall length as unknown, then later update it after a contractor response or better visual evidence. The current implementation does not need to populate prior values yet, but the schema supports history structurally.

## 3. Input manifest as ingestion envelope

I created `data/input/manifest.json` instead of hardcoding file paths in extractors. In production, this manifest would be created by the intake/upload layer from customer submissions and object-storage metadata. In this repo, it is checked in as a deterministic fixture so extractor runs are reproducible.

Stable `capture_id` values are important because they connect raw inputs to provenance. For example, an observation can point back to `text_note_001`, `photo_001`, or `drawing_floor_plan_001`.

## 4. Extractor architecture

I considered three options:

1. One monolithic extractor that reads every input and produces the final scope.
2. A heavy plugin/factory/registry system for extractors.
3. A lightweight strategy-style interface where every modality extractor returns a shared `ExtractorResult`.

I chose option 3.

Each modality extractor behaves like a strategy behind a shared protocol: text, audio, drawing, and vision. Each extractor returns partial evidence, not the final `ScopeBrief`. Fusion happens later.

I intentionally avoided a heavyweight factory/registry because the assignment has four known modalities. If Donizo later adds multiple providers per modality, I would introduce routing keyed by modality, provider, confidence threshold, latency, and cost.

## 5. Text extractor

The French note is short enough to parse with deterministic rules, but production contractor notes will not always be short or clean. They may contain mixed trades, slang, missing details, multilingual phrasing, or contradictions.

I therefore used an LLM-backed text extractor behind a `TextModelClient` boundary. The extractor is not hardcoded to showers. It asks the model for a structured draft containing observations, tasks, materials, assumptions, clarifying questions, confidence, and evidence quotes.

The internal output is normalized to English even when the input is French. This keeps downstream fusion, eval, and pricing contracts stable across languages. Original French evidence is still preserved in the raw normalized draft through evidence quotes.

Unit tests use fake model clients so they do not spend API credits or depend on provider availability. The real CLI command runs the OpenAI-backed text extractor once and saves the typed `ExtractorResult` to `data/output/text_note_001.json`.

This was influenced by a GenAI requirements-processing system I worked on. A naive section-by-section pipeline generated repeated follow-up questions because it lacked whole-document context. We improved results by carrying document summaries and prior Q&A into each step. That experience influenced the choice to keep extraction structured, contextual, and testable.

## 6. Audio extractor scaffold

I implemented a `Transcriber` protocol and a `MockTranscriber`, instead of implementing real speech-to-text immediately.

The audio flow is:

audio capture → transcriber → transcript → text model client → `ExtractorResult`

This satisfies the assignment requirement that the signature should be ready to swap in faster-whisper without changing downstream code. The mock transcriber reads a synthetic French transcript fixture and returns text, language, confidence, and segments.

## 7. Two-pass drawing parser

The assignment explicitly requires a two-pass drawing parser, so I made that separation visible in code:

1. geometry pass: extracts room outline, primitives, labels, visible dimensions, and geometry confidence from the drawing image.
2. semantic pass: infers layout meaning, work-area context, ambiguity, candidate verification task, and clarifying questions from the geometry summary.

The parser is now OpenAI-backed for both passes, but it remains conservative. It does not treat unitless or ambiguous sketch dimensions as pricing-grade measurements. Instead, it preserves them in the raw geometry summary and surfaces missing/uncertain dimensions as clarifying questions.

The first real drawing run was too eager to create electrical/carpentry/door tasks from drawing-only symbols. I tightened the semantic prompt so drawing-only evidence mostly becomes existing-state observations, risks, and verification questions unless another modality confirms requested work.

This is still one of the parts I am least confident in for production. It is architecturally correct and works for this fixture, but real reliability would require a drawing benchmark with clean plans, messy hand-drawn plans, conflicting dimensions, fixture symbols, and human-labeled expected geometry. I would measure dimension recall, unit correctness, symbol false positives, and whether unsupported drawing details leak into priced scope.

## 8. Vision extractor and model routing

I implemented a generic vision extractor with an OpenAI model client. The model is configurable through environment variables.

For routine real calls, I plan to use GPT-5.4. GPT-5.5 is reserved as an edge-path model for low-confidence, blurry, or conflicting inputs.

This is a cost/accuracy tradeoff. The most expensive model should not be the default for every image if a cheaper strong model is sufficient. The vision extractor asks the model to be conservative: extract visible existing-state facts, image quality, unclear regions, uncertainty, and pricing risks. It should only suggest tasks or materials when visually supported.

## 9. Pricing readiness gate

I included an explicit pricing-readiness gate instead of only returning a final JSON scope.

A scope can be useful but not pricing-ready. The extraction layer should not silently pass low-confidence or incomplete scopes to downstream pricing.

Current criteria include:

- title exists
- description exists
- at least one task exists
- no must-have clarifying questions
- average task confidence is above threshold
- no unresolved critical conflicts

## 10. What I would ask the contractor

Before final pricing, I would ask:

- Where exactly should the two showers be located?
- What is the length and position of the new placo wall?
- Is the 100mm evacuation existing, accessible, and compliant for two showers?
- What water heater type and capacity are expected?
- Are waterproofing, floor slope, tiling, electrical work, and finishes included?
- Which drawn lines are existing walls, new partitions, or openings?

These should remain clarifying questions unless confirmed by stronger evidence.

## 11. Output files

The first real call on `photo_001` produced structurally valid output but suggested photo-only candidate tasks too aggressively. I have improved the vision prompt to prefer observations and clarifying questions over tasks unless the image clearly supports requested work. The initial output is kept as `data/output/vision_photo_01_before_improved_prompt.json`; the corrected run is `data/output/vision_photo_01.json`.

## 12. Real extraction and cached output workflow

After the initial scaffold, I moved the pipeline from mostly mocked extraction to real model-backed extraction for text, drawing, vision, and fusion.

The final flow is:

1. run each modality extractor once
2. save typed `ExtractorResult` JSON outputs
3. reuse saved outputs during fusion
4. run one final LLM-assisted fusion call
5. validate the final `ScopeBrief` with deterministic eval

I chose this because it gives a better production shape than calling every model repeatedly during final scope generation. It also makes debugging easier: if fusion output is wrong, I can inspect whether the issue came from text extraction, drawing pass 1, drawing pass 2, vision extraction, or fusion.

This also helped with prompt calibration. For example, early vision and drawing outputs produced candidate tasks too aggressively from visual evidence alone. I tightened the prompts so visual modalities mostly produce existing-state observations, risks, and clarifying questions unless another modality supports requested work.

## Why fusion is LLM-assisted but gated by code

I did not want fusion to be a hardcoded shower-job assembler. The fusion layer uses an LLM to synthesize across modalities because it needs to combine contractor text, visual context, drawing uncertainty, and missing pricing inputs.

However, I kept deterministic code responsible for:

- schema validation
- provenance attachment
- confidence propagation
- pricing readiness
- eval checks

This is the balance I would use in production: let the model synthesize messy evidence, but let code enforce the contract and block unsafe pricing.

## Eval result interpretation

The deterministic eval passed all curated assertions, but I do not treat that as proof that the model is generally solved. It means the current output satisfies the job-specific checks I defined: required scope items are present, missing pricing blockers are preserved, pricing readiness is false, and the system avoids specific hallucinations like `floor_area_m2` and TVA category.

A broader production eval would need more jobs, more drawing variants, adversarial photos, and human-labeled expected outputs.


# Kill your darling

The part of the design I am least confident in is the drawing extraction layer.

I like the two-pass design: first extract geometry, then infer semantics from that geometry. It makes the reasoning traceable and prevents the model from jumping directly from a hand-drawn plan to a priced scope.

But I do not yet trust it enough for pricing-grade quantity extraction.

The current implementation correctly treats the drawing as uncertain context. It extracts visible dimensions and symbols, but does not use ambiguous or unitless measurements as final quantities. That is safe, but it also means the drawing parser is not yet delivering its full value.

The next thing I would test is a small labeled drawing benchmark:

- clean floor plans with known dimensions
- messy hand-drawn plans
- unitless dimensions
- conflicting dimensions
- fixture symbols
- openings and partition lines

I would measure:

- dimension recall
- dimension precision
- unit correctness
- whether a dimension is attached to the correct wall/segment
- symbol false positives
- how often drawing-only details become unsupported tasks

If this benchmark shows weak dimension or symbol precision, I would keep the drawing parser as context-only and require human confirmation before pricing. If it performs well on measured plans, I would let it contribute more directly to quantity takeoff, but still behind the pricing-readiness gate.
