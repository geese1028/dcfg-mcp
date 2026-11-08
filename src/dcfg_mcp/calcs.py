"""Pure calculation functions. No MCP dependency, so they can be unit-tested directly.

Every function returns a plain dict that is safe to serialise as JSON.
"""

from __future__ import annotations

import math
from typing import Optional

SOURCE_SITE = "https://datacenterfieldguides.com"

# ---------------------------------------------------------------------------
# 1. Liquid-loop hydraulics
# ---------------------------------------------------------------------------

# Default fluid properties. These are typical values only; always override them
# with the coolant supplier's datasheet at the actual operating temperature.
COOLANTS = {
    # Treated water, approx. 30-35 degC
    "water": {"rho": 995.0, "cp": 4.18, "mu": 0.00075},
    # 25 % propylene glycol by weight, approx. 30-35 degC
    "pg25": {"rho": 1020.0, "cp": 3.95, "mu": 0.0018},
}

# DCFG field guideline for stainless pipe and EPDM hose (not a code limit).
VELOCITY_GUIDELINE_M_S = 3.0

# Unit conversions
_PSI_TO_KPA = 6.894757
_LPM_TO_USGPM = 0.2641720524


def _darcy_friction_factor(reynolds: float, rel_roughness: float) -> float:
    """Darcy friction factor: laminar 64/Re, turbulent Swamee-Jain."""
    if reynolds <= 0:
        raise ValueError("Reynolds number must be positive")
    if reynolds < 2300:
        return 64.0 / reynolds
    return 0.25 / (math.log10(rel_roughness / 3.7 + 5.74 / reynolds**0.9)) ** 2


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
    """Size coolant flow from heat and Delta-T, then estimate velocity and pressure drop.

    Q = m_dot * cp * dT
    dP_pipe = (lambda * L / D + sum(zeta)) * rho * v^2 / 2
    dP_coupling = SG * (Q_gpm / Cv)^2   [psi], per coupling in series
    """
    if heat_kw <= 0:
        raise ValueError("heat_kw must be > 0")
    if delta_t_k <= 0:
        raise ValueError("delta_t_k must be > 0")
    if pipe_inner_diameter_mm <= 0:
        raise ValueError("pipe_inner_diameter_mm must be > 0")
    if pipe_length_m < 0 or sum_local_loss_coefficients < 0:
        raise ValueError("pipe_length_m and sum_local_loss_coefficients must be >= 0")

    key = coolant.lower()
    if key not in COOLANTS and None in (density_kg_m3, specific_heat_kj_kgk, viscosity_pa_s):
        raise ValueError(
            f"Unknown coolant '{coolant}'. Use one of {sorted(COOLANTS)} "
            "or supply density_kg_m3, specific_heat_kj_kgk and viscosity_pa_s."
        )
    props = dict(COOLANTS.get(key, {}))
    if density_kg_m3 is not None:
        props["rho"] = density_kg_m3
    if specific_heat_kj_kgk is not None:
        props["cp"] = specific_heat_kj_kgk
    if viscosity_pa_s is not None:
        props["mu"] = viscosity_pa_s
    rho, cp, mu = props["rho"], props["cp"], props["mu"]

    # Thermal balance
    m_dot = heat_kw / (cp * delta_t_k)  # kg/s
    q_m3_s = m_dot / rho
    q_lpm = q_m3_s * 60_000.0

    # Velocity
    d = pipe_inner_diameter_mm / 1000.0
    area = math.pi * d**2 / 4.0
    v = q_m3_s / area
    reynolds = rho * v * d / mu
    dynamic_pressure_pa = rho * v**2 / 2.0

    # Pipe friction + local losses
    friction = None
    dp_friction_kpa = 0.0
    if pipe_length_m > 0:
        friction = _darcy_friction_factor(reynolds, (pipe_roughness_mm / 1000.0) / d)
        dp_friction_kpa = friction * (pipe_length_m / d) * dynamic_pressure_pa / 1000.0
    dp_local_kpa = sum_local_loss_coefficients * dynamic_pressure_pa / 1000.0

    # Quick-disconnect couplings from published Cv
    couplings = []
    dp_couplings_kpa = 0.0
    sg = rho / 999.0
    q_gpm = q_lpm * _LPM_TO_USGPM
    for cv in coupling_cv or []:
        if cv <= 0:
            raise ValueError("coupling Cv values must be > 0")
        dp = sg * (q_gpm / cv) ** 2 * _PSI_TO_KPA
        couplings.append({"cv": cv, "pressure_drop_kpa": round(dp, 2)})
        dp_couplings_kpa += dp

    total_kpa = dp_friction_kpa + dp_local_kpa + dp_couplings_kpa

    flags = []
    if v > VELOCITY_GUIDELINE_M_S:
        flags.append(
            f"VELOCITY {v:.2f} m/s exceeds the {VELOCITY_GUIDELINE_M_S} m/s DCFG field guideline "
            "for stainless pipe / EPDM hose. Increase the pipe size or split the flow."
        )
    if 2300 <= reynolds < 4000:
        flags.append("TRANSITIONAL flow (2300 <= Re < 4000): friction estimate is uncertain.")
    if key not in COOLANTS or any(
        x is not None for x in (density_kg_m3, specific_heat_kj_kgk, viscosity_pa_s)
    ):
        fluid_note = "User-supplied fluid properties."
    else:
        fluid_note = (
            f"Default '{key}' properties used. Replace them with the coolant datasheet "
            "values at the actual operating temperature before you sign anything."
        )

    return {
        "inputs": {
            "heat_kw": heat_kw,
            "delta_t_k": delta_t_k,
            "pipe_inner_diameter_mm": pipe_inner_diameter_mm,
            "coolant": key,
            "density_kg_m3": rho,
            "specific_heat_kj_kgk": cp,
            "viscosity_pa_s": mu,
            "pipe_length_m": pipe_length_m,
            "sum_local_loss_coefficients": sum_local_loss_coefficients,
        },
        "flow": {
            "mass_flow_kg_s": round(m_dot, 4),
            "volumetric_flow_l_min": round(q_lpm, 2),
            "volumetric_flow_us_gpm": round(q_gpm, 2),
            "flow_per_kw_l_min": round(q_lpm / heat_kw, 4),
        },
        "velocity": {
            "mean_velocity_m_s": round(v, 3),
            "reynolds_number": round(reynolds),
            "darcy_friction_factor": None if friction is None else round(friction, 5),
        },
        "pressure_drop_kpa": {
            "pipe_friction": round(dp_friction_kpa, 2),
            "local_losses": round(dp_local_kpa, 2),
            "couplings": couplings,
            "couplings_total": round(dp_couplings_kpa, 2),
            "total": round(total_kpa, 2),
        },
        "flags": flags,
        "notes": [
            fluid_note,
            "This is a design estimate. Acceptance needs a measured flow and differential "
            "pressure from calibrated instruments over a stable dwell window.",
        ],
        "equations": [
            "m_dot = Q_heat / (cp * dT)",
            "dP = (lambda * L / D + sum_zeta) * rho * v^2 / 2",
            "dP_coupling[psi] = SG * (Q[gpm] / Cv)^2",
        ],
        "source": f"{SOURCE_SITE}/blog/nvl72-liquid-load-bank-testing-guide",
    }


# ---------------------------------------------------------------------------
# 2. SOP / MOP / EOP classification
# ---------------------------------------------------------------------------


def classify_procedure(
    task_description: str,
    service_or_person_in_danger_now: bool,
    changes_redundancy_or_topology: bool,
    repeatable_routine_task: bool,
    has_point_of_no_return: bool = False,
    has_back_out_plan: bool = False,
    approved_before_work: bool = False,
) -> dict:
    """Classify a task as SOP, MOP or EOP and list what the paper must contain.

    Test order follows the DCFG rule "the test is the clock":
    danger now -> EOP; changes the plant and must come back -> MOP;
    same way every time -> SOP; otherwise it is not yet a procedure.
    """
    missing: list[str] = []
    rules: list[str] = []

    if service_or_person_in_danger_now:
        cls = "EOP"
        meaning = "Emergency Operating Procedure"
        verdict = "PROCEED_WITH_EOP"
        rules = [
            "Execute the stabilising steps only. Do not troubleshoot inside the EOP.",
            "The EOP stops at the first stable safe state.",
            "Any repair after the safe state is new work and needs its own MOP.",
        ]
    elif changes_redundancy_or_topology:
        cls = "MOP"
        meaning = "Method of Procedure"
        if not has_point_of_no_return:
            missing.append("An explicit Point of No Return (PONR)")
        if not has_back_out_plan:
            missing.append("A pre-verified back-out sequence")
        if not approved_before_work:
            missing.append("Approval before the tools come out")
        verdict = "REFUSE_UNTIL_COMPLETE" if missing else "READY"
        rules = [
            "One job, one day, one plant change, with a named owner.",
            "The MOP is approved before work starts, not during it.",
        ]
    elif repeatable_routine_task:
        cls = "SOP"
        meaning = "Standard Operating Procedure"
        verdict = "READY"
        rules = [
            "The SOP must not change redundancy or switching topology.",
            "If a step would isolate equipment, that step belongs in a MOP.",
        ]
    else:
        cls = "UNDEFINED"
        meaning = "Not yet a procedure"
        verdict = "WRITE_IT_DOWN"
        rules = [
            "The task is neither routine, nor a plant change, nor an emergency response.",
            "Describe it more precisely, or write it down before you call it a procedure.",
        ]

    rules.append(
        "A Permit to Work (PTW) controls who, where and when. It is an administrative gate, "
        "not a fourth kind of procedure."
    )

    return {
        "task": task_description,
        "classification": cls,
        "meaning": meaning,
        "verdict": verdict,
        "missing_items": missing,
        "rules": rules,
        "source": f"{SOURCE_SITE}/blog/sop-mop-eop",
    }


# ---------------------------------------------------------------------------
# 3. ANSI/ISA-71.04-2013 corrosion coupon classification
# ---------------------------------------------------------------------------

# Upper bounds (exclusive) in Angstrom per 30 days. GX is anything at or above the last bound.
_CU_BOUNDS = [("G1", 300.0), ("G2", 1000.0), ("G3", 2000.0)]
_AG_BOUNDS = [("G1", 200.0), ("G2", 1000.0), ("G3", 2000.0)]
_SEVERITY = {"G1": "Mild", "G2": "Moderate", "G3": "Harsh", "GX": "Severe"}
_ORDER = ["G1", "G2", "G3", "GX"]


def _classify(rate: float, bounds: list[tuple[str, float]]) -> str:
    for name, upper in bounds:
        if rate < upper:
            return name
    return "GX"


def normalize_to_30_days(film_angstrom: float, exposure_days: float) -> float:
    """R30 = X_film * 30 / T_days (linear normalisation)."""
    if exposure_days <= 0:
        raise ValueError("exposure_days must be > 0")
    if film_angstrom < 0:
        raise ValueError("film thickness must be >= 0")
    return film_angstrom * 30.0 / exposure_days


def classify_corrosion_coupon(
    copper_film_angstrom: float,
    exposure_days: float,
    silver_film_angstrom: Optional[float] = None,
    copper_blank_angstrom: Optional[float] = None,
    silver_blank_angstrom: Optional[float] = None,
) -> dict:
    """Classify a copper/silver coupon result under ANSI/ISA-71.04-2013 thresholds.

    The room class is the worse of the two metals. Without silver, a G1 claim is refused.
    Field blanks are reported but never subtracted automatically.
    """
    cu_rate = normalize_to_30_days(copper_film_angstrom, exposure_days)
    cu_class = _classify(cu_rate, _CU_BOUNDS)

    flags: list[str] = []
    ag_rate = ag_class = None
    if silver_film_angstrom is not None:
        ag_rate = normalize_to_30_days(silver_film_angstrom, exposure_days)
        ag_class = _classify(ag_rate, _AG_BOUNDS)
        overall = max(cu_class, ag_class, key=_ORDER.index)
        g1_claim_allowed = overall == "G1"
    else:
        overall = cu_class
        g1_claim_allowed = False
        flags.append(
            "NO SILVER COUPON: a copper result alone cannot prove G1 for lead-free (RoHS) "
            "hardware. Classification is copper-only and incomplete."
        )

    if not 20 <= exposure_days <= 40:
        flags.append(
            f"EXPOSURE {exposure_days} days is far from 30 days. Linear normalisation assumes "
            "a constant corrosion rate, so treat the result with caution."
        )

    if copper_blank_angstrom is None and silver_blank_angstrom is None:
        flags.append(
            "NO FIELD BLANK reported. Handling or shipping contamination cannot be ruled out."
        )
    else:
        for metal, blank in (("copper", copper_blank_angstrom), ("silver", silver_blank_angstrom)):
            if blank is not None and blank > 0:
                flags.append(
                    f"The {metal} field blank shows {blank} Angstrom. It is reported, not subtracted. "
                    "Ask the lab whether the exposed result is still valid."
                )

    if overall == "G1" and g1_claim_allowed:
        verdict = "PASS_G1"
    elif silver_film_angstrom is None and overall == "G1":
        verdict = "INCOMPLETE_NEEDS_SILVER"
    else:
        verdict = "FAIL_ABOVE_G1"

    return {
        "copper": {
            "rate_angstrom_per_30d": round(cu_rate, 1),
            "class": cu_class,
            "severity": _SEVERITY[cu_class],
        },
        "silver": None
        if ag_rate is None
        else {
            "rate_angstrom_per_30d": round(ag_rate, 1),
            "class": ag_class,
            "severity": _SEVERITY[ag_class],
        },
        "room_class": overall,
        "room_severity": _SEVERITY[overall],
        "verdict": verdict,
        "flags": flags,
        "thresholds_angstrom_per_30d": {
            "copper": {"G1": "<300", "G2": "300-<1000", "G3": "1000-<2000", "GX": ">=2000"},
            "silver": {"G1": "<200", "G2": "200-<1000", "G3": "1000-<2000", "GX": ">=2000"},
        },
        "equations": ["R30 = X_film * 30 / T_days", "room class = worse of copper and silver"],
        "source": f"{SOURCE_SITE}/blog/data-center-corrosion-coupon-isa-71-04-guide",
    }
