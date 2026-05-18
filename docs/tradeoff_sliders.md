# Tradeoff Sliders

As per deliverables, this document records the positions I would take for the first production version of the scope modeling system. These are not permanent rules; they are operating defaults that should be revisited as evaluation data grows.

## 1. Cost vs Accuracy

### Position

I would not trade 5% extraction accuracy for 50% cost reduction on fields that directly affect pricing, scope boundaries, or compliance. I would consider that trade for low-impact descriptive fields.

### My line

I split fields into two groups:

**Pricing-critical fields**
- task existence
- quantities
- dimensions
- drainage/water/electrical requirements
- regulatory constraints
- must-have clarifying questions
- confidence and provenance

For these, I would favor accuracy. A false saving on model cost can become expensive if it causes a wrong quote, missed scope, or bad contractor/customer experience.

**Non-critical fields**
- wording of description
- title phrasing
- cosmetic observations
- low-impact nice-to-have questions

For these, I would trade some accuracy for cost reduction.

### Current implementation choice

The vision model is configurable through environment variables. For routine photo extraction, I plan to use GPT-5.4. GPT-5.5 is reserved as an edge-path model, not the default.

The intended routing is:

- routine path: GPT-5.4
- cheaper path later: smaller model for clean, low-risk photos
- edge path: GPT-5.5 only when confidence is low, image quality is poor, or modalities conflict
- stop condition: after bounded retries/escalation, route to human review instead of unlimited model calls

### Why

In construction pricing, the cost of a wrong structured scope can be much higher than the cost of a model call. But not every field deserves the same model budget. The system should spend more where the business risk is higher.

## 2. Latency vs Robustness

### Position

For this use case, I would choose 90s P95 at 99% reliability over 30s at 90% reliability.

### Why

The brief says the contractor expects a structured proposal in their inbox in 1 hour. That means the product does not require sub-30-second real-time response for this workflow.

A 30s system that silently fails or produces incomplete outputs 10% of the time is worse than a 90s system that reliably returns a traceable result, clear gaps, and a pricing-readiness decision.

### Current implementation choice

The service is local-first and async-shaped. Each modality extractor can run independently:

- text
- audio transcript
- drawing
- photos

This naturally supports parallel execution later, but the current implementation prioritizes correctness and traceability over premature latency optimization.

### Production default

My default would be:

- run cheap/high-confidence extractors first
- run image/model calls in parallel where possible
- use timeouts per modality
- preserve partial results
- return a not-ready scope with clarifying questions instead of failing the whole job
- escalate to human review when required evidence is missing

### Failure posture

If one provider is slow or unavailable, the system should not block forever. It should degrade into:

- alternate provider if available and within cost ceiling
- lower-confidence partial result
- explicit gap
- human review route

## 3. Schema Strictness vs Evolvability

### Position

I would keep the outer contract strict and the domain vocabulary moderately flexible.

### What should be strict

The pricing engine needs reliable structure. These should be strict:

- top-level `ScopeBrief` shape
- provenance format
- confidence bounds
- task ordering
- gap severity
- pricing-readiness criteria
- source capture IDs
- required task fields: name, category, point A, point B

Strictness here prevents downstream consumers from receiving unpredictable data.

### What should stay evolvable

The construction vocabulary should not be over-constrained too early:

- task categories
- material names
- fixture/component labels
- observation labels
- regulatory classifications
- trade-specific terms

The assignment explicitly introduces a second job type later: façade renovation on a Haussmannian building. That is a different regulatory and spatial model from a wine-bar shower installation. If the schema were too plumbing-specific, it would fail that migration.

### Current implementation choice

The schema uses typed core structures but leaves room for new task categories and observations. The current model supports this shower job while remaining adaptable to façade work.

### Why

A domain expert may join later and revise the vocabulary. If we overfit the schema today, migration becomes expensive. If we make everything free-form, the pricing engine becomes unreliable.

The right compromise is:

- strict envelope
- typed provenance/confidence
- strict gap severity
- controlled but extendable categories
- versioned fields for mutable extracted values
- migration notes whenever schema meaning changes
