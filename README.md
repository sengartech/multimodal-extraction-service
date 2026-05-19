# Donizo Multimodal Extraction Service

Local-first Python service for converting messy multimodal renovation inputs into a typed `ScopeBrief` for downstream pricing/review.

The project processes:

- French contractor text
- site photos
- a hand-drawn floor plan
- mocked audio transcript
- saved extractor outputs
- LLM-assisted fusion
- deterministic eval

The implementation is intentionally local-first: extractors can be run once, their typed JSON outputs are saved, and fusion/eval can reuse those outputs without rerunning every model call.

## What this builds

For the wine-bar shower assignment, the system produces:

```text
data/output/scope_brief.json
```

The final scope includes:

- title and description
- site context
- ordered tasks with Point A / Point B
- materials and estimated quantities
- assumptions and exclusions
- ranked clarifying questions
- confidence and provenance
- pricing-readiness gate
- schema version
- support for future façade-style work areas/access/regulatory requirements

The final output is intentionally `not_ready` for pricing while must-have blockers remain.

## Requirements

- Python 3.12
- OpenAI API key
- Pydantic v2
- pytest

## Setup

```bash
conda create -p .venv python=3.12

conda activate ./.venv

pip install -e .

pip install -e ".[dev]"
```

Create `.env`:

```bash
cp .env.example .env
```

Add:

```env
OPENAI_API_KEY=your_key_here

TEXT_MODEL=gpt-5.4
VISION_MODEL=gpt-5.4
DRAWING_GEOMETRY_MODEL=gpt-5.4
DRAWING_SEMANTIC_MODEL=gpt-5.4
FUSION_MODEL=gpt-5.4
```

Model env vars are optional; the code has defaults.

## Input fixture

The normalized input manifest is:

```text
data/input/manifest.json
```

It points to:

```text
data/input/customer_text_fr.txt
data/input/audios/mock_voice_note_fr.txt
data/input/drawings/floor_plan.png
data/input/photos/photo_01.png
data/input/photos/photo_02.png
...
```

In production, the manifest would be created by the upload/intake layer from object storage metadata and customer/job metadata.

## Run extractors

### Text extraction

```bash
scope-modeler extract-text \
  --capture-id text_note_001 \
  --output data/output/text_note_001.json
```

### Vision extraction

Run selected photos and save typed outputs:

```bash
scope-modeler extract-vision \
  --capture-id photo_001 \
  --output data/output/vision_photo_01.json

scope-modeler extract-vision \
  --capture-id photo_002 \
  --output data/output/vision_photo_02.json
```

### Drawing extraction

The drawing parser is explicitly two-pass:

1. image → geometry summary
2. geometry summary → semantic inference

```bash
scope-modeler extract-drawing \
  --capture-id drawing_floor_plan_001 \
  --output data/output/drawing_result.json
```

Audio is intentionally mocked for this assignment through the transcript fixture.

## Build final scope

Fusion reads saved extractor outputs and runs one LLM-assisted fusion call:

```bash
scope-modeler build-scope \
  --text-output data/output/text_note_001.json \
  --drawing-output data/output/drawing_result.json \
  --vision-output data/output/vision_photo_01.json \
  --vision-output data/output/vision_photo_02.json \
  --output data/output/scope_brief.json
```

Validate JSON:

```bash
python -m json.tool data/output/scope_brief.json > /tmp/scope_check.json
```

## Run eval

```bash
scope-modeler eval-scope \
  --scope data/output/scope_brief.json \
  --output data/output/eval_results.json
```

The eval harness is deterministic and assertion-based. It checks required job facts, pricing blockers, and hallucination safety checks such as not inventing `floor_area_m2` or TVA category.

## Run tests

```bash
pytest -v
```

The test suite covers:

- schema invariants
- OpenAI strict schema conversion
- extractor contracts
- text extraction
- vision extraction
- two-pass drawing parser
- fusion
- assignment-required cross-modal disagreement case
- incomplete input validation
- eval harness
- façade schema migration

## Project layout

```text
src/scope_modeler/
  cli.py
  inputs.py
  models/
    scope.py
    provenance.py
    versioned.py
    enums.py
  extractors/
    text.py
    vision.py
    drawing.py
    audio.py
  fusion/
    fusion_engine.py
    readiness.py
  llm/
    openai_client.py
    schema.py
  eval/
    harness.py

tests/
docs/
data/input/
data/output/
```

## Important outputs

```text
data/output/text_note_001.json
data/output/drawing_result.json
data/output/vision_photo_01.json
data/output/vision_photo_02.json
data/output/scope_brief.json
data/output/eval_results.json
```

Some initial/calibration outputs may also be present to show prompt iteration, for example early vision/drawing outputs before tightening prompts.

## Design notes

The pipeline uses LLMs where messy interpretation is useful, but code owns the contract:

- Pydantic schemas validate structure.
- Provenance is attached to extracted/fused fields.
- Pricing readiness is computed deterministically.
- Eval is deterministic and does not use an LLM judge.
- Saved extractor outputs avoid rerunning expensive model calls during fusion/eval.

For missing or uncertain pricing-critical inputs, the system should ask clarifying questions instead of hallucinating quantities or regulatory decisions.

## Docs

- All docs as per listed deliverables are in `docs` folder.
- AI conversation history is also attached as docs and available in `docs/ai_conversation_history.md`.
