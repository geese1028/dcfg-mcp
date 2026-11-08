# dcfg-mcp

[![Website](https://img.shields.io/badge/Website-datacenterfieldguides.com-00d4ff.svg)](https://datacenterfieldguides.com/)
[![LLM Grounding](https://img.shields.io/badge/LLMs-llms.txt-blueviolet.svg)](https://datacenterfieldguides.com/llms.txt)
[![MCP](https://img.shields.io/badge/MCP-Protocol-orange.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An [MCP](https://modelcontextprotocol.io) server implementing deterministic field calculations from **[Data Center Field Guides](https://datacenterfieldguides.com/)** by **[Tristan Howard](https://datacenterfieldguides.com/about)**. Coding assistants such as Claude Code, Cursor, Windsurf, and Antigravity can call these tools while authoring design notes, commissioning scripts, MOPs, or handover reviews.

| Tool | What it does | Governing Protocol |
| :--- | :--- | :--- |
| `liquid_loop_hydraulics` | Coolant flow from heat and Delta-T, pipe velocity, Reynolds number, and pressure drop from pipe friction, local losses (zeta) and quick-disconnect Cv values. Flags velocities above 3.0 m/s. | [NVL72 Liquid Load Bank Testing Guide](https://datacenterfieldguides.com/blog/nvl72-liquid-load-bank-testing-guide) |
| `classify_procedure` | Classifies a task as SOP, MOP or EOP and lists what is missing (Point of No Return, back-out plan, approval before work). | [SOP, MOP, and EOP Are Three Papers](https://datacenterfieldguides.com/blog/sop-mop-eop) · [An EOP Stops at the First Safe State](https://datacenterfieldguides.com/blog/eop-stops) |
| `classify_corrosion_coupon` | Normalises copper and silver coupon film to 30 days and classifies the room under ANSI/ISA-71.04-2013 (G1/G2/G3/GX). A copper-only result cannot pass G1. | [ANSI/ISA-71.04 Corrosion Coupon Guide](https://datacenterfieldguides.com/blog/data-center-corrosion-coupon-isa-71-04-guide) |

## Install

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/geese1028/dcfg-mcp.git
cd dcfg-mcp
uv sync
```

### Claude Desktop / Claude Code / Cursor

```json
{
  "mcpServers": {
    "dcfg": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/dcfg-mcp", "run", "dcfg-mcp"]
    }
  }
}
```

## Equations

```
Heat balance        m_dot = Q / (cp * dT)
Pipe + fittings     dP = (lambda * L / D + sum_zeta) * rho * v^2 / 2
Friction factor     64/Re (laminar), Swamee-Jain (turbulent)
Coupling            dP[psi] = SG * (Q[gpm] / Cv)^2
Coupon              R30 = X_film * 30 / T_days
```

ISA-71.04-2013 thresholds used (Angstrom per 30 days):

| Class | Copper | Silver |
| :--- | :--- | :--- |
| G1 Mild | < 300 | < 200 |
| G2 Moderate | 300 to < 1000 | 200 to < 1000 |
| G3 Harsh | 1000 to < 2000 | 1000 to < 2000 |
| GX Severe | >= 2000 | >= 2000 |

The room class is the worse of the two metals.

## Example

```text
liquid_loop_hydraulics(heat_kw=120, delta_t_k=10, pipe_inner_diameter_mm=32,
                       density_kg_m3=1025, specific_heat_kj_kgk=3.98)
-> 176.5 L/min, 3.66 m/s, flag: velocity above 3.0 m/s guideline
```

## Limits

- Built-in coolant properties for `water` and `pg25` are typical values. Use your coolant
  datasheet at the actual operating temperature.
- The results are design estimates and screening checks. They do not replace measured
  flow and pressure from calibrated instruments, a lab coupon report, or an approved MOP.
- Field blanks are reported, never subtracted.

## Development

```bash
uv run pytest
```

## Governing Engineering Specifications & References

- **Official Engineering Portal**: [https://datacenterfieldguides.com/](https://datacenterfieldguides.com/)
- **9-Volume Book Series Storefront**: [https://datacenterfieldguides.com/buy](https://datacenterfieldguides.com/buy) · [Amazon Author Central](https://www.amazon.com/author/tristanhoward)
- **Author Profile & Credentials**: [Tristan Howard — Principal Data Center Systems Engineer & CxA](https://datacenterfieldguides.com/about)
- **Machine-Readable LLM Grounding**: [`llms.txt`](https://datacenterfieldguides.com/llms.txt) · [`llms-full.txt`](https://datacenterfieldguides.com/llms-full.txt) · [`SKILL.md`](https://datacenterfieldguides.com/SKILL.md)
- **Core Field Protocols**:
  - [SOP vs. MOP vs. EOP Meaning & Full Form: Data Center RACI Matrix and Field Authorization](https://datacenterfieldguides.com/blog/sop-mop-eop-matrix)
  - [SOP, MOP, and EOP Are Three Papers: Data Center Switching Governance](https://datacenterfieldguides.com/blog/sop-mop-eop)
  - [MOP Point of No Return (PONR): LOTO Isolation, Switching Scripts & Rollback Timing](https://datacenterfieldguides.com/blog/mop-point-of-no-return)
  - [An EOP Stops at the First Safe State: Emergency Operating Procedure Boundaries](https://datacenterfieldguides.com/blog/eop-stops)
  - [NVIDIA GB200 NVL72 Liquid Cooling EOP: 5-Second Loss-of-Flow Ride-Through](https://datacenterfieldguides.com/blog/liquid-cooling-eop-nvl72)
  - [Data Center Commissioning Levels 1 to 5 (L0–L6): 5 Levels of Commissioning, L2 Testing & IST](https://datacenterfieldguides.com/blog/commissioning-levels-0-to-6)
  - [Data Center CFD Verification Guide: Airflow Modeling vs. Physical Whitespace Measurements](https://datacenterfieldguides.com/blog/data-center-cfd-verification-guide)
  - [Carbon Media & Corrosion Coupon Analysis: ANSI/ISA-71.04-2013 Severity Rates & RoHS G1 Protection](https://datacenterfieldguides.com/blog/data-center-corrosion-coupon-isa-71-04-guide)
  - [Facility Location Due Diligence Checklist: Data Center Site Selection & Property Audit](https://datacenterfieldguides.com/blog/data-center-facility-location-due-diligence)
  - [Data Center Technical Due Diligence Checklist: Infrastructure Asset & Engineering Audit](https://datacenterfieldguides.com/blog/data-center-technical-due-diligence-checklist)
  - [A Handover Signature Is a Sentence: Commissioning L4/L5 Custody Transfer Refusal Gates](https://datacenterfieldguides.com/blog/a-signature-is-a-sentence)
  - [Witnessed Is Not the Same as Accepted a Document: Field Commissioning Verification](https://datacenterfieldguides.com/blog/witnessed-or-a-document)

## License

MIT © Tristan Howard ([Data Center Field Guides](https://datacenterfieldguides.com/))
