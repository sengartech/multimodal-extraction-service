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

## Actual call cost evidence

I used OpenAI for the real model-backed extraction and fusion calls in this assignment.

Screenshots from the OpenAI project usage dashboard are included here:

- `docs/screenshots/donizo-openai-usage-summary.png`
- `docs/screenshots/donizo-openai-usage-logs.png`

I did not use Anthropic for the final submitted run, so no Anthropic console screenshot is included.

## Approximate cost per call

| Stage | Calls made | Notes |
|---|---:|---|
| Text extraction | 3 | French contractor note to structured evidence |
| Vision extraction | 3 final calls + calibration rerun(s) | Saved photo outputs reused in fusion |
| Drawing extraction | 2 calls per run, total 4 | Geometry pass + semantic pass |
| Fusion | 2 | Saved extractor outputs to final `ScopeBrief` |
| Eval | 0 model calls | Deterministic local code |

The OpenAI console screenshot is the source of truth for actual spend. I did not optimize aggressively for the assignment because correctness and traceability mattered more than minimizing a few cents of model usage.

---

Total OpenAI spend for assignment run: $0.37

Approximate cost per final pipeline run: ~ $0.5

## Degraded mode: provider outage during peak

If the primary provider is down for 4 hours during peak, the system should degrade by preserving intake and avoiding uncontrolled fallback spend.

For this assignment I used OpenAI, but the same policy would apply if Anthropic were the primary provider.

### What changes

During degraded mode:

- accept and store new jobs normally
- do not repeatedly retry failed model calls
- use cached extractor outputs if they already exist
- run deterministic validation/eval only where possible
- allow cheap text-only extraction if available
- pause expensive image/drawing extraction unless explicitly approved
- mark affected jobs as `not_ready` instead of forcing a low-confidence scope
- route urgent jobs to human review
- we can implement fallback LLM provider so if one fails it can switch to another.

### Hard cost ceiling

I would set a hard degraded-mode ceiling of **$0.50 per job** until the primary provider is healthy again.

That budget is enough for limited text/fusion fallback, but not enough for repeated image/drawing retries.
