# Migration

## Context

The initial schema was built around the wine-bar shower job: interior work, photos, a floor plan, plumbing tasks, a placo partition, drainage, and a water heater.

The schema handled that case well, but the assignment also asks it to support a different job type: `ravalement de façade` on a Haussmannian apartment building.

That case is different:

- the work area is not a room
- the main surface is the entire street-facing façade
- scaffolding may be required
- regulatory and ownership approvals may block execution
- the relevant regime may include déclaration préalable, Bâtiments de France, and copropriété authorization

## What was generalized

I generalized the schema from an interior-room assumption to a broader work-area model.

The new `WorkArea` model can represent:

- room
- wall
- façade
- zone
- unknown area

This lets the same `ScopeBrief` represent both:

- an interior shower/changing-room job
- an exterior façade renovation job

The existing `tasks`, `materials`, `clarifying_questions`, `provenance`, and `pricing_readiness` models remain unchanged.

## What was added

I added three optional schema sections:

### `work_areas`

Represents the physical area affected by the job.

For the façade case, this can describe:

- street-facing façade
- whole exterior wall surface
- optional `surface_m2` when known

### `access_requirements`

Represents access and site setup constraints.

For the façade case, this can describe:

- scaffolding required
- street access
- protection requirements
- occupant or building coordination

### `regulatory_requirements`

Represents approvals or compliance checks that may block execution.

For the facade case, this can describe:

- déclaration préalable
- Bâtiments de France review in protected zones
- copropriété authorization
- TVA/regulatory category when supported

These fields are optional and default to empty lists, so existing shower outputs remain valid.

## What was deprecated

Nothing was removed or renamed.

I intentionally avoided deprecating the existing `site_context` field because it is still useful as a human-readable summary. The new fields make structured access/regulatory/work-area data available without breaking existing consumers.

## Why the initial schema did not generalize

The initial schema was too biased toward interior renovation scopes: it could describe tasks and materials, but it did not have first-class fields for exterior work areas, access setup like scaffolding, or regulatory approvals that can block façade work.

## Compatibility

This migration is backward compatible.

Existing `ScopeBrief` objects without `work_areas`, `access_requirements`, or `regulatory_requirements` still validate because the new fields have default empty lists.

## Test coverage

The migration should include tests for:

- old shower-style `ScopeBrief` validation
- new facade-style `ScopeBrief` validation
- scaffolding as an access requirement
- déclaration préalable / Bâtiments de France / copropriété as regulatory requirements
- pricing readiness remaining blocked when regulatory or must-have blockers exist

## Implemented

The schema now includes:

- `WorkArea`
- `AccessRequirement`
- `RegulatoryRequirement`

`ScopeBrief` has optional/default `work_areas`, `access_requirements`, and `regulatory_requirements` lists. Blocking regulatory requirements now contribute to the deterministic pricing-readiness gate via `blocking_regulatory_requirements`.
