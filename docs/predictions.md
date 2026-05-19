# Predictions

Before running eval, I expect the system to perform best on explicit contractor-text facts and weaker on fields that require measurement, product specification, or regulatory assumptions.

| Field Type | Predicted Precision | Predicted Recall | Reason |
|---|---:|---:|---|
| Requested tasks | 0.90 | 0.85 | The text clearly states two showers, placo wall, wall opening, drainage, and water heater connection. |
| Measurements / quantities | 0.75 | 0.55 | Some values are explicit, such as 2 showers, 2 m wall height, and evacuation 100. Wall length, room dimensions, fixture counts, and water heater capacity are missing or uncertain. |
| Materials | 0.75 | 0.60 | Placo, water heater, and drainage connection are extractable, but exact shower fixtures, waterproofing, finishes, and fittings are underspecified. |
| Existing-state context | 0.80 | 0.65 | Photos and drawing provide useful context, but visual evidence should remain conservative. |
| Clarifying questions / blockers | 0.85 | 0.80 | Missing pricing blockers are clear: wall length, shower fixture scope, waterproofing, room dimensions, water heater spec, and access constraints. |
| Pricing readiness | 0.95 | 0.95 | The scope should be marked not ready because must-have questions remain. |
| Regulatory / TVA fields | 0.40 | 0.20 | The input does not provide enough information to confidently assign TVA or regulatory category. |

I expect the eval to show high quality on explicit scope extraction, good safety on pricing readiness, and lower recall on quantities and regulatory fields. I would rather the system leave fields unknown than hallucinate pricing-grade details.