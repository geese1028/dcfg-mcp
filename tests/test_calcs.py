import math

import pytest

from dcfg_mcp import calcs


# ---------------- hydraulics ----------------

def test_flow_from_heat_balance_matches_hand_calc():
    # 120 kW, dT 10 K, cp 3.98, rho 1025 -> 3.015 kg/s -> 176.5 L/min
    r = calcs.liquid_loop_hydraulics(
        heat_kw=120, delta_t_k=10, pipe_inner_diameter_mm=32,
        density_kg_m3=1025, specific_heat_kj_kgk=3.98, viscosity_pa_s=0.0018,
    )
    assert r["flow"]["mass_flow_kg_s"] == pytest.approx(3.0151, abs=1e-3)
    assert r["flow"]["volumetric_flow_l_min"] == pytest.approx(176.5, abs=0.1)


def test_velocity_in_dn32_and_guideline_flag():
    # 176.5 L/min in a 32 mm bore: 2.94e-3 m3/s / 8.04e-4 m2 = 3.66 m/s (> 3.0 guideline)
    r = calcs.liquid_loop_hydraulics(
        heat_kw=120, delta_t_k=10, pipe_inner_diameter_mm=32,
        density_kg_m3=1025, specific_heat_kj_kgk=3.98, viscosity_pa_s=0.0018,
    )
    assert r["velocity"]["mean_velocity_m_s"] == pytest.approx(3.657, abs=0.01)
    assert any(f.startswith("VELOCITY") for f in r["flags"])


def test_local_loss_equals_zeta_times_dynamic_pressure():
    r = calcs.liquid_loop_hydraulics(
        heat_kw=50, delta_t_k=10, pipe_inner_diameter_mm=40, coolant="water",
        sum_local_loss_coefficients=4.0,
    )
    rho = calcs.COOLANTS["water"]["rho"]
    v = r["velocity"]["mean_velocity_m_s"]
    expected_kpa = 4.0 * rho * v**2 / 2 / 1000
    assert r["pressure_drop_kpa"]["local_losses"] == pytest.approx(expected_kpa, rel=1e-2)


def test_coupling_cv_pressure_drop():
    # Choose heat so flow = 110 L/min of water-like fluid (rho 999 -> SG 1.0)
    rho, cp, dt = 999.0, 4.18, 10.0
    heat_kw = 110 / 60000 * rho * cp * dt
    r = calcs.liquid_loop_hydraulics(
        heat_kw=heat_kw, delta_t_k=dt, pipe_inner_diameter_mm=32,
        density_kg_m3=rho, specific_heat_kj_kgk=cp, viscosity_pa_s=0.00075,
        coupling_cv=[12.5],
    )
    # 110 L/min = 29.06 gpm; (29.06/12.5)^2 = 5.40 psi = 37.3 kPa
    assert r["pressure_drop_kpa"]["couplings_total"] == pytest.approx(37.3, abs=0.3)


def test_friction_factor_laminar_and_turbulent():
    assert calcs._darcy_friction_factor(1000, 0.0) == pytest.approx(0.064)
    # Smooth pipe, Re 1e5: Moody chart ~0.018
    assert calcs._darcy_friction_factor(1e5, 0.0) == pytest.approx(0.018, abs=0.001)


def test_hydraulics_rejects_bad_input():
    with pytest.raises(ValueError):
        calcs.liquid_loop_hydraulics(heat_kw=0, delta_t_k=10, pipe_inner_diameter_mm=32)
    with pytest.raises(ValueError):
        calcs.liquid_loop_hydraulics(heat_kw=10, delta_t_k=10, pipe_inner_diameter_mm=32, coolant="oil")


# ---------------- procedures ----------------

def test_emergency_is_eop_even_if_it_changes_topology():
    r = calcs.classify_procedure("UPS fire alarm", True, True, False)
    assert r["classification"] == "EOP"


def test_mop_missing_items_refused():
    r = calcs.classify_procedure("Put UPS-A in maintenance bypass", False, True, False)
    assert r["classification"] == "MOP"
    assert r["verdict"] == "REFUSE_UNTIL_COMPLETE"
    assert len(r["missing_items"]) == 3


def test_complete_mop_ready():
    r = calcs.classify_procedure("Chiller 2 isolation", False, True, False, True, True, True)
    assert r["verdict"] == "READY"
    assert r["missing_items"] == []


def test_routine_is_sop_and_unknown_is_undefined():
    assert calcs.classify_procedure("Daily round", False, False, True)["classification"] == "SOP"
    assert calcs.classify_procedure("Something", False, False, False)["verdict"] == "WRITE_IT_DOWN"


# ---------------- corrosion ----------------

def test_normalisation():
    assert calcs.normalize_to_30_days(260, 26) == pytest.approx(300.0)


def test_boundary_300_is_g2_for_copper():
    r = calcs.classify_corrosion_coupon(260, 26, silver_film_angstrom=100, copper_blank_angstrom=0)
    assert r["copper"]["class"] == "G2"
    assert r["room_class"] == "G2"
    assert r["verdict"] == "FAIL_ABOVE_G1"


def test_silver_drives_room_class():
    r = calcs.classify_corrosion_coupon(150, 30, silver_film_angstrom=1500, copper_blank_angstrom=0)
    assert r["copper"]["class"] == "G1"
    assert r["silver"]["class"] == "G3"
    assert r["room_class"] == "G3"


def test_copper_only_cannot_pass_g1():
    r = calcs.classify_corrosion_coupon(120, 30)
    assert r["verdict"] == "INCOMPLETE_NEEDS_SILVER"
    assert any("NO SILVER" in f for f in r["flags"])


def test_clean_pair_passes_g1():
    r = calcs.classify_corrosion_coupon(120, 30, silver_film_angstrom=90,
                                        copper_blank_angstrom=0, silver_blank_angstrom=0)
    assert r["verdict"] == "PASS_G1"
    assert r["flags"] == []


def test_gx():
    r = calcs.classify_corrosion_coupon(2000, 30, silver_film_angstrom=50, copper_blank_angstrom=0)
    assert r["room_class"] == "GX"
