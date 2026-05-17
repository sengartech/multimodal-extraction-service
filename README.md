# Donizo Multimodal Extraction Service

Local-first Python scaffold for converting messy multimodal renovation inputs into a typed
structured specification for a downstream pricing engine.

This repository is intentionally minimal at this stage. It establishes the package structure,
tooling, placeholders, and test runner only. Business logic, model calls, fusion logic, drawing
parsing, audio transcription, and pricing readiness checks will be added in later iterations.

## Target Inputs

- French contractor text note about creating two staff changing-room showers
- Hand-drawn floor plan
- Photos of the existing space
- Audio extractor scaffold with a mock French transcriber

## Planned Output

A Pydantic v2 `ScopeBrief` / `Job` object with:

- Title and description
- Ordered tasks
- Initial state / Point A per task
- Final state / Point B per task
- Materials and estimated quantities
- Assumptions and exclusions
- Ranked clarifying questions
- Confidence and provenance per field
- Version/history support for mutable fields
- Pricing-readiness gate with explicitly computed criteria

## Requirements

- Python 3.12
- Pydantic v2
- pytest
- OpenAI SDK
- Optional Anthropic SDK
- Local CLI entrypoint, no web server

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Optional Anthropic SDK:

```bash
pip install -e ".[anthropic,dev]"
```

## Run

```bash
scope-modeler --help
```

Or without installing the console script:

```bash
python -m scope_modeler --help
```

## Test

```bash
pytest
```

## Project Layout

```text
src/scope_modeler/
  cli.py
  models/
  extractors/
  fusion/
  eval/
tests/
docs/
data/input/
data/output/
```
