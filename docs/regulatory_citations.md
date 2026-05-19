# Regulatory Citations

I am not a French construction regulatory expert, so I am not treating these references as final compliance decisions. I looked them up as likely applicable references for this job and would expect a French domain expert to validate them before production use.

The purpose of this file is to show how regulatory references could be linked to extracted schema fields so the system knows where compliance-sensitive checks may be needed.

| Reference | Why it may apply | Schema field(s) |
|---|---|---|
| **NF DTU 60.1 — Plomberie sanitaire pour bâtiments** | The job includes creating two showers and installing/connecting a water heater. NF DTU 60.1 covers sanitary plumbing in buildings, including cold/hot water pipework and sanitary equipment connections. | `tasks[]`, `materials[]`, `clarifying_questions[]`, `pricing_readiness` |
| **NF DTU 25.41 — Ouvrages en plaques de plâtre** | The contractor note asks for a 2 m non-full-height `placo` partition wall. NF DTU 25.41 covers plasterboard works such as partitions, counter-partitions, and ceilings. | `tasks[]`, `materials[]`, `clarifying_questions[]` |
| **NF DTU 52.2 — Pose collée des revêtements céramiques / SPEC** | The job involves creating shower areas. Waterproofing and finishes are not specified, but wet-area protection under tile may be relevant if the shower scope includes tiled walls/floors. NF DTU 52.2 includes provisions around bonded ceramic finishes and SPEC when required. | `clarifying_questions[]`, `exclusions[]`, `pricing_readiness` |

## How this affects the current scope

The final `ScopeBrief` should not assign compliance status automatically.

For this job, the system should keep pricing readiness as `not_ready` until the contractor confirms:

- shower fixture and waterproofing scope
- wall length and placo build-up
- water heater type/capacity/electrical requirements
- whether the existing drainage route is compliant and reusable
- whether finish/tile works are included

This is why the current system asks clarifying questions instead of claiming final regulatory compliance.
