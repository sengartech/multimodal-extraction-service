# Cost and Routing

This project uses real model calls for text, drawing, vision, and fusion, but avoids repeating those calls unnecessarily.

## Routing used in this assignment

| Stage | Model path | Output |
|---|---|---|
| Text extraction | OpenAI structured text call | `data/output/text_note_001.json` |
| Drawing geometry pass | OpenAI image structured call | first-pass geometry inside `drawing_result.json` |
| Drawing semantic pass | OpenAI text structured call over geometry summary | second-pass semantic inference inside `drawing_result.json` |
| Vision extraction | OpenAI image structured call for selected photos | `vision_photo_01.json`, `vision_photo_02.json` |
| Fusion | OpenAI structured text call over saved extractor results | `scope_brief.json` |
| Eval | deterministic local code | `eval_results.json` |

## Why outputs are cached

Each modality extractor writes a typed `ExtractorResult` JSON file. Fusion reads those saved outputs instead of rerunning every model call.

This gives three benefits:

1. cost control: expensive image/model calls are not repeated during every fusion run
2. reproducibility: the same saved evidence can be inspected and reused
3. debugging: if the final scope is wrong, I can check whether the issue came from text, drawing, vision, or fusion

## Model selection

For this assignment, I used `gpt-5.4` as the default model for real extraction and fusion calls.

I would not use the strongest available model for every request by default in production. A better routing policy would be:

- cheaper/smaller model for clean text or high-quality images
- stronger model for blurry images, ambiguous drawings, or conflicting modalities
- human review when confidence remains low after bounded retries

## Retry and escalation policy

I would keep retries bounded.

Example production policy:

1. run default extractor
2. if schema validation fails, retry once with the same model
3. if confidence is low or modalities conflict, escalate once to a stronger model
4. if still unresolved, mark pricing as not ready and ask clarifying questions or send to human review

The system should not keep calling models until it gets a convenient answer.

## Human review threshold

A job should be routed to human review or contractor follow-up when:

- must-have clarifying questions remain
- pricing readiness is false
- drawing dimensions are ambiguous
- photos are blurry or do not show the work area
- text and visual evidence conflict
- regulatory or TVA assumptions are required but not supported

For this job, the final scope is intentionally `not_ready` for pricing because fixture details, wall length, waterproofing, water heater specs, exact room dimensions, and access conditions are unresolved.

## Prompt calibration

I kept initial real outputs when they revealed useful calibration issues.

Early vision and drawing runs were structurally valid but too eager to create tasks from visual evidence alone. I tightened prompts so visual modalities mostly produce existing-state observations, risks, and clarifying questions unless requested work is supported by text or another modality.

That calibration is part of cost control too: better prompts reduce repeated calls and reduce the chance of expensive downstream mistakes.