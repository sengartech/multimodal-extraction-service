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

The French note is short enough to parse with deterministic rules, but production contractor notes will not always be short or clean. They may contain mixed trades, slang, missing details, or contradictions.

I therefore used a generic LLM-backed text extractor boundary with a fake model client for tests. The extractor is not hardcoded to showers. It expects a structured draft containing observations, tasks, materials, assumptions, and clarifying questions.

Unit tests use fake clients so they do not spend API credits or depend on provider availability.

This was influenced by a GenAI requirements-processing system I worked on. A naive section-by-section pipeline generated repeated follow-up questions because it lacked whole-document context. We improved results by carrying document summaries and prior Q&A into each step. That experience influenced the choice to keep extraction structured, contextual, and testable.

## 6. Audio extractor scaffold

I implemented a `Transcriber` protocol and a `MockTranscriber`, instead of implementing real speech-to-text immediately.

The audio flow is:

audio capture → transcriber → transcript → text model client → `ExtractorResult`

This satisfies the assignment requirement that the signature should be ready to swap in faster-whisper without changing downstream code. The mock transcriber reads a synthetic French transcript fixture and returns text, language, confidence, and segments.

## 7. Two-pass drawing parser

The assignment explicitly requires a two-pass drawing parser, so I made that separation visible in code:

1. `pass_1_extract_geometry`: extracts dimensions, primitives, labels, and geometry confidence.
2. `pass_2_infer_semantics`: infers work area, possible walls/openings, candidate layout task, and clarifying questions.

The current parser is deterministic and conservative. It does not pretend to extract precise dimensions from the hand-drawn plan. Instead, it surfaces missing measurements as must-have clarifying questions.

This is the part of the design I am least confident in. It is architecturally compliant, but it does not yet perform real OCR, line detection, scale inference, or geometry extraction. If I continued this work, I would build a drawing benchmark with clean plans, messy hand-drawn plans, conflicting dimensions, and fixture symbols, then measure dimension recall and false positives.

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