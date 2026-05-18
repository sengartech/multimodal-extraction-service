# AI Usage Log

This assignment allows AI assistance. I used AI tools as implementation accelerators, but kept architecture decisions, tradeoffs, and final code review under my control.

## Included AI assistance

I used Codex inside VS Code for implementation support on:

- project scaffold
- Pydantic schema implementation
- input manifest loader
- extractor contracts
- generic text extractor boundary
- audio extractor scaffold
- two-pass drawing parser
- vision extractor implementation
- unit test generation and small refactors

## Human decisions made during implementation

### Project shape

I chose a local-first Python CLI/service-style project rather than a FastAPI server. The assignment risk is extraction, schema design, confidence/provenance, evaluation, and production reasoning — not HTTP routing or deployment.

### Schema design

I chose a generic construction-aware `ScopeBrief` schema instead of a shower-specific schema. The goal was to support the provided wine-bar shower case while keeping the model evolvable for the later façade renovation migration.

### Provenance and confidence

I chose field-level provenance and confidence instead of only a job-level confidence score. This makes extracted facts auditable and helps later fusion decide which modality to trust.

### Extractor architecture

I treated extractors as lightweight strategies behind a shared protocol. I intentionally avoided a factory, plugin system, or dependency injection container because the assignment has a small fixed set of modalities.

### Text extraction

I chose a generic LLM-backed text extractor boundary rather than hardcoded shower-specific parsing. Tests use a fake model client so unit tests do not call real APIs.

### Audio extraction

I implemented a `Transcriber` protocol and `MockTranscriber`, keeping the signature ready for a future faster-whisper implementation without changing downstream extraction code.

### Drawing parsing

I implemented the drawing parser as explicitly two-pass: geometry extraction first, semantic inference second. The current implementation is conservative because the hand-drawn plan should not be treated as a precise measurement source.

### Vision extraction

I implemented an OpenAI-backed vision extractor with a fake client for tests. Real API calls are intentionally separated from unit tests and will be run explicitly on selected photos.

### Model routing

I configured GPT-5.4 as the routine model for vision extraction and reserved GPT-5.5 as a potential edge-path model for low-confidence, blurry, or conflicting inputs.

## Excluded from shared log

This repository log focuses on implementation-related AI usage. Private planning, interview preparation, and unrelated personal notes are excluded.

## Review process

For each AI-generated code change, I reviewed:

- whether it matched the assignment requirement
- whether it was over-engineered
- whether tests stayed deterministic
- whether real API calls were avoided in unit tests
- whether provenance and confidence were preserved
- whether the implementation remained explainable in a Loom walkthrough
