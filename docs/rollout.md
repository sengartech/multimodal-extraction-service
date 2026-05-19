# Rollout

## Week 1

Ship the narrowest useful vertical slice:

- ingest one contractor text note, photos, and one drawing
- produce a typed `ScopeBrief`
- preserve provenance and confidence
- generate must-have clarifying questions
- mark pricing readiness as ready/not ready
- save intermediate extractor outputs for debugging
- run deterministic eval on a small curated job set

The goal is not full automation. The goal is to make the extraction trace inspectable and safe.

## Week 4

Expand from one fixture to a small internal benchmark of real jobs:

- bathrooms/showers
- simple plumbing jobs
- wall/partition jobs
- jobs with bad photos
- jobs with ambiguous drawings
- jobs with conflicting customer text and photos

By week 4, I would expect:

- field-level eval by category
- known failure buckets
- prompt/model routing policy
- human review queue for not-ready jobs
- dashboard for extraction errors and pricing blockers
- regression tests for over-inference from photos/drawings

## Behind a feature flag for 90 days

These should stay behind a feature flag:

- auto-pricing from extracted scope
- regulatory/TVA classification
- drawing-derived quantities used directly for takeoff
- automatic acceptance of visual-only tasks
- customer-facing summaries without human review

The system can suggest, but should not silently commit these outputs until eval shows they are safe.

## What gets killed

I would kill any extraction path that does not improve eval or reduce human review load.

Examples:

- a drawing parser that extracts many dimensions but cannot map them correctly
- a vision prompt that creates tasks from existing-state photos
- a fusion step that produces nicer summaries but worse blockers
- a model route that costs more without improving field-level precision/recall

The rule is simple: if it does not improve grounded scope quality, pricing readiness, or review speed, it does not stay.
