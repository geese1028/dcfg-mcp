"""MCP server exposing the DCFG field calculations over stdio."""

from __future__ import annotations

from typing import Optional

from mcp.server.mcpserver import MCPServer

from . import __version__, calcs

mcp = MCPServer(
    name="dcfg-data-center-field-guides",
    title="Data Center Field Guides",
    version=__version__,
    website_url="https://datacenterfieldguides.com",
    instructions=(
        "Field calculations for data center engineering: liquid-cooling loop hydraulics, "
        "SOP/MOP/EOP classification, and ANSI/ISA-71.04 corrosion coupon classification. "
        "Results are design estimates and screening checks, not acceptance records."
    ),
)


@mcp.tool()
def liquid_loop_hydraulics(
    heat_kw: float,
    delta_t_k: float,
    pipe_inner_diameter_mm: float,
    coolant: str = "pg25",
    density_kg_m3: Optional[float] = None,
    specific_heat_kj_kgk: Optional[float] = None,
    viscosity_pa_s: Optional[float] = None,
    pipe_length_m: float = 0.0,
    pipe_roughness_mm: float = 0.015,
    sum_local_loss_coefficients: float = 0.0,
    coupling_cv: Optional[list[float]] = None,
) -> dict:
    """Size a liquid-cooling loop (for example an NVL72 rack or a liquid load bank).

    Computes the required coolant flow from heat load and Delta-T (Q = m_dot * cp * dT),
    the mean velocity in the pipe, and the pressure drop from pipe friction, local loss
    coefficients (zeta) and quick-disconnect couplings (from published Cv values).
    coolant: "water" or "pg25" (25 % propylene glycol), or pass your own density,
    specific heat and viscosity. Flags velocities above the 3.0 m/s field guideline.
    """
    return calcs.liquid_loop_hydraulics(
        heat_kw=heat_kw,
        delta_t_k=delta_t_k,
        pipe_inner_diameter_mm=pipe_inner_diameter_mm,
        coolant=coolant,
        density_kg_m3=density_kg_m3,
        specific_heat_kj_kgk=specific_heat_kj_kgk,
        viscosity_pa_s=viscosity_pa_s,
        pipe_length_m=pipe_length_m,
        pipe_roughness_mm=pipe_roughness_mm,
        sum_local_loss_coefficients=sum_local_loss_coefficients,
        coupling_cv=coupling_cv,
    )


@mcp.tool()
def classify_procedure(
    task_description: str,
    service_or_person_in_danger_now: bool,
    changes_redundancy_or_topology: bool,
    repeatable_routine_task: bool,
    has_point_of_no_return: bool = False,
    has_back_out_plan: bool = False,
    approved_before_work: bool = False,
) -> dict:
    """Classify a data center task as SOP, MOP or EOP and list what the paper is missing.

    EOP: a service or person is in danger now; it stops at the first safe state.
    MOP: the work changes redundancy or switching topology; it needs a Point of No Return,
    a back-out plan and approval before work. SOP: a repeatable routine that never changes
    redundancy. A Permit to Work is an administrative gate, not a fourth procedure.
    """
    return calcs.classify_procedure(
        task_description=task_description,
        service_or_person_in_danger_now=service_or_person_in_danger_now,
        changes_redundancy_or_topology=changes_redundancy_or_topology,
        repeatable_routine_task=repeatable_routine_task,
        has_point_of_no_return=has_point_of_no_return,
        has_back_out_plan=has_back_out_plan,
        approved_before_work=approved_before_work,
    )


@mcp.tool()
def classify_corrosion_coupon(
    copper_film_angstrom: float,
    exposure_days: float,
    silver_film_angstrom: Optional[float] = None,
    copper_blank_angstrom: Optional[float] = None,
    silver_blank_angstrom: Optional[float] = None,
) -> dict:
    """Classify a corrosion coupon result under ANSI/ISA-71.04-2013 (G1/G2/G3/GX).

    Normalises the measured film thickness to 30 days (R30 = X * 30 / T), classifies copper
    and silver separately, and reports the room class as the worse of the two. A copper-only
    result cannot prove G1. Field blanks are reported but never subtracted.
    """
    return calcs.classify_corrosion_coupon(
        copper_film_angstrom=copper_film_angstrom,
        exposure_days=exposure_days,
        silver_film_angstrom=silver_film_angstrom,
        copper_blank_angstrom=copper_blank_angstrom,
        silver_blank_angstrom=silver_blank_angstrom,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
