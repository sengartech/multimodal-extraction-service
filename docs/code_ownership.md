# Code Ownership

These are five lines I consider least obvious in the implementation. I picked lines where the code is doing more than simple data mapping.

| File | Line | Code | What it does | Why it matters |
|---|---:|---|---|---|
| `src/scope_modeler/llm/schema.py` | 21 | `node.clear()` | Removes every sibling key from a JSON schema node that contains `$ref`. | OpenAI strict structured output rejects `$ref` combined with keys like `default` or `description`. This line prevents schema errors caused by Pydantic-generated schemas. |
| `src/scope_modeler/llm/schema.py` | 27 | `node["required"] = list(properties.keys())` | Makes every property required for object schemas before sending them to OpenAI. | OpenAI strict mode expects all object properties to be listed in `required`. Without this, model calls failed even though the Pydantic models were valid. |
| `src/scope_modeler/extractors/drawing.py` | 206 | `f"{geometry_summary.model_dump_json()}\n\n"` | Passes only the first-pass drawing geometry summary into the semantic pass. | This keeps the drawing parser genuinely two-pass. The second model does not re-read the image directly; it reasons from extracted geometry, which makes failures easier to debug. |
| `src/scope_modeler/fusion/fusion_engine.py` | 185 | `evidence_bundle = build_evidence_bundle(job_id, source_captures, extractor_results)` | Converts all extractor outputs into one normalized evidence bundle before fusion. | Fusion should not work from raw files. It should synthesize from typed evidence so provenance, modality boundaries, and intermediate outputs remain inspectable. |
| `src/scope_modeler/eval/harness.py` | 235 | `status: Literal["pass", "fail", "partial"] = "pass" if not matched_terms else "fail"` | Handles negative assertions, where the correct result is that certain terms are absent. | Some eval checks are about avoiding hallucinations. For example, `floor_area_m2` and TVA category should not appear unless the input supports them. |
