# Tradeoff Sliders

This document records the positions I would take for the first production version of the scope modeling system. These are operating defaults, not permanent rules.

## 1. Cost vs Accuracy

### Position

I would not trade 5% extraction accuracy for 50% cost reduction on pricing-critical fields.

My line is:

- no cost tradeoff for fields that affect scope, quantities, pricing readiness, safety, or compliance
- cost tradeoff is acceptable for low-risk descriptive fields

### Rationale

A cheaper model is not actually cheaper if it causes a wrong quote, missed scope, or unnecessary contractor/customer back-and-forth.

For this assignment, I used real model calls for text, drawing, vision, and fusion, but cached the typed outputs. That gives accuracy where needed while avoiding repeated calls during fusion and eval.

### Where I would save cost

I would use cheaper models for:

- clean text notes
- high-quality photos with simple extraction
- formatting/summarization
- non-critical description wording

I would use stronger models for:

- blurry photos
- ambiguous drawings
- cross-modal conflicts
- final fusion when pricing blockers must be ranked correctly

## 2. Latency vs Robustness

### Position

I would choose **90s P95 at 99% reliability** over **30s at 90% reliability**.

### Rationale

This workflow does not need a real-time answer. The contractor expects a structured proposal workflow, not a chat response in a few seconds.

A fast system that silently produces incomplete or wrong scope 10% of the time is worse than a slower system that reliably returns:

- extracted scope
- provenance
- confidence
- missing fields
- pricing readiness status

### Practical design choice

The current implementation supports this direction by saving intermediate extractor outputs:

- text output
- drawing output
- vision outputs
- final scope output

That makes the pipeline easier to retry, inspect, and debug. If one modality fails, the system can still preserve partial evidence instead of losing the whole job.

## 3. Schema Strictness vs Evolvability

### Position

I would keep the outer contract strict and the domain vocabulary moderately flexible.

### Strict today

These should be strict because downstream systems depend on them:

- `ScopeBrief` structure
- task fields
- material fields
- provenance format
- confidence range
- gap severity
- pricing readiness
- schema version
- source capture references

This prevents malformed or ambiguous output from reaching pricing.

### Flexible today

These should remain more evolvable:

- task categories
- material/component vocabulary
- fixture names
- room/space labels
- regulatory classifications
- trade-specific terms

The reason is simple: a domain expert joining in three months may rewrite how components and transformations should be named. If the vocabulary is too rigid now, migration becomes expensive.

### Rationale

The schema should protect the business contract without pretending that the construction ontology is already final.

For this assignment, I used a versioned schema and generic construction-aware fields instead of a shower-specific schema. That lets the system handle the current shower job while still leaving room for future cases like façade renovation, different trades, and improved domain vocabulary.