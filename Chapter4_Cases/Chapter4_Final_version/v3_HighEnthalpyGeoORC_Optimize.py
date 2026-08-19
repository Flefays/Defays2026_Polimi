# -*- coding: utf-8 -*-
"""
Created on Thu Aug  6 2026 -- revised

@author: flori

OPTIMIZATION: Geothermal ORC Power Plant (High-Enthalpy Two-Phase Resource)

Description:
    Pymoo optimisation for each working fluid
    and saves the results (optimal points + full evaluation logs)
    The diagram generation is done separately in v3_HighEnthalpyGeoORC_diagrams.py.

    Two variables: p_evap and dT_cd.

    p_evap stays subcritical:

        0.15 * p_crit <= p_evap <= min(0.90 * p_crit, p_sat(T_geo - dT_pp_evap - dT_margin))

    The turbine inlet is always saturated vapour (r0.x = 1), 
    so T_evap = T_sat(p_evap) and the geosteam evaporator pinch,
    T_geo - T_sat, is exactly what the upper bound on p_evap protects. 
    
    The upper constraint is 0.9*p_crit, but could be limited by the pinch imposed
    at the brine evaporator. 
    
    The only constraint is the re_injection temperature

Note:
    Since pinch points are imposed in the model, they can be defined as variables.

    Since I used CSV files with pandas, the model incorporates
    HighEnthalpyGeoORC.get_parameter() which forces NaN on every read
    after self._solved is False (see the Template).
    
    Examining the situation without the constraint is useful for determining 
    whether the constraint is feasible during execution. (pymoo G gives it after)
    
AI USAGE:
    After understanding the problem, the AI ​​was asked to create "_feasible_mask"
    to filter the log directly in these cases.
"""

import numpy as np
import pandas as pd
from CoolProp.CoolProp import PropsSI as PSI
from pymoo.algorithms.soo.nonconvex.de import DE

from v3_HighEnthalpyGeoORC_Template import HighEnthalpyGeoORC


# -----------------------------------------------------------
# p_evap bounds (subcritical only)
# -----------------------------------------------------------
def p_evap_bounds(fluid, T_geo, dT_pp_evap=10.0, frac_lo=0.15, frac_hi=0.90, dT_margin=2.0, p_min_abs=1.05):
    """
    Returns (p_lo, p_hi) in bar, and always subcritical.

    dT_margin keeps T_geo - T_sat(p_evap) strictly above dT_pp_evap. 
    It's made to add a buffer when computing p_hi, avoiding Jacobian 
    singularity.
    
    """
    T_crit = PSI("Tcrit", fluid) - 273.15
    p_crit = PSI("Pcrit", fluid) / 1e5
    T_evap_max = T_geo - dT_pp_evap - dT_margin

    p_hi = frac_hi * p_crit
    if T_evap_max < T_crit:
        p_sat_cap = PSI("P", "T", T_evap_max + 273.15, "Q", 1, fluid) / 1e5
        p_hi = min(p_hi, p_sat_cap)

    p_lo = max(min(frac_lo * p_crit, 0.5 * p_hi), p_min_abs) # Security (fct of working-fluid properties). 
    return float(round(p_lo, 3)), float(round(p_hi, 3))      # Round to 3 decimals


# -----------------------------------------------------------
# Optimisation Settings & Execution
# -----------------------------------------------------------

T_geo   = 160             # °C
m_geo   = 180             # kg/s
x_steam = 0.1             # [-]
T_inj_constraint = 70     # °C
                          
T_amb = 15                # °C
P_amb = 0.6               # bar

dT_cd = 15                # °C
dT_pp_evap = 10           # geobrine evaporator ttd_l 
dT_pp_cond = 10           # condenser td_pinch 
dT_ap_pre  = 5            # preheater outlet (approach point); x_r4 = 0 (for dT_ap_pre=0)

cooling_fluid = "air"

algorithm = DE(pop_size=40)  # the seed can be fixed (seed=n)
termination = ("n_gen", 30)

all_results = {}
summary_rows = []

for fluid in ["n-Pentane", "Isopentane", "Cyclopentane", "n-Butane"]:

    print(f"\n{'='*40}")
    print(f"  Fluid: {fluid}")
    print(f"{'='*40}")

    p_lo, p_hi = p_evap_bounds(fluid, T_geo, dT_pp_evap=dT_pp_evap)
    p_crit = PSI("Pcrit", fluid) / 1e5
    print(f"  p_evap in [{p_lo:.2f}, {p_hi:.2f}] bar "
          f"([{p_lo/p_crit:.2f}, {p_hi/p_crit:.2f}] p_crit)")

    model = HighEnthalpyGeoORC(
        working_fluid       = fluid,
        cooling_fluid        = cooling_fluid,
        geofluidTemperature = T_geo,
        geofluidFlow        = m_geo,
        geofluidVapour      = x_steam,
        evaporationPressure = 0.5 * (p_lo + p_hi),
        T_amb               = T_amb,
        P_amb               = P_amb,
        dT_cd               = dT_cd,
        dT_pp_evap          = dT_pp_evap,
        dT_pp_cond          = dT_pp_cond,
        dT_ap_pre           = dT_ap_pre,
    )

    # Variables, Constraints, Objectives, Tracking
    variables = {"p_evap": {"min": p_lo, "max": p_hi},
                 "dT_cd": {"min": 5, "max": 30}}
    constraints = {"T_injection": {"min": T_inj_constraint}}
    objective = ["net_power"]
    minimize_flags = [False]   # False -> maximise
    kpi = [
        "T_injection", "p_evap", "dT_cd", "p_ratio_crit",
        "T_turbine_in", "T_preheater_out", "m_workingfluid",
        "evap_steam_UA", "evap_brine_UA", "preheater_UA",
        "evap_steam_pinch", "evap_brine_pinch","preheater_ttd_min", 
        "thermal_efficiency",
    ]

    # ! In tespy v0.10.2, .optimize() returns a (log_df, pymoo_result) tuple
    log_df, opt_result = model.optimize(
        algorithm      = algorithm,
        termination    = termination,
        variables      = variables,
        constraints    = constraints,
        objective      = objective,
        minimize_flags = minimize_flags,
        kpi            = kpi,
    )

    # Filter out NaNs for convergence failures 
    mask = ~np.isnan(log_df["net_power"].values)
    data = log_df.loc[mask].copy()

    # Export the full evaluation log for this fluid
    data.to_csv(f"optim_log_{fluid}.csv", index=False)

    if data.empty:
        print("\n  [!] No converged point at all for this fluid.")
        all_results[fluid] = {"log": data, "best_unconstrained": None, "best_constrained": None}
        continue

    # --- Best Unconstrained ---
    best_unc = data.loc[data["net_power"].idxmax()]
    print("\n--- Best (unconstrained) ---")
    print(f"  p_evap      : {best_unc['p_evap']:.3f} bar ({best_unc['p_ratio_crit']:.2f} p_crit)")
    print(f"  net power   : {best_unc['net_power']:.2f} MW")
    print(f"  T_injection : {best_unc['T_injection']:.2f} degC")

    # --- Best Constrained ---
    """
    read from pymoo's res.X / res.F / res.CV.' T_injection' is passed via 
    'constraints', so pymoo does feasibility selection for it. Filtering the 
    log afterwards on 'T_injection' alone would miss any other constraint added
    to 'constraints' later without updating the filter too. 
    (this happened before while using isobutane).
    
    ! res.X can end up None even when the log clearly contains feasible points.
    Seen in practice, most likely the DE population lost track of a good individual.
    When that happens, fall back to filtering the log directly.
    
    """
    
    def _feasible_mask(df, constraints):
        mask = np.ones(len(df), dtype=bool)
        for param, bounds in constraints.items():
            if param not in df.columns:
                continue
            if "min" in bounds:
                mask &= df[param].values >= bounds["min"]
            if "max" in bounds:
                mask &= df[param].values <= bounds["max"]
        return mask

    best_con = None
    if opt_result is not None and opt_result.X is not None:
        cv = getattr(opt_result, "CV", None)
        # If pymoo populates X, a missing CV implies the solution is feasible (CV <= 0)
        is_feasible = bool(cv is None or np.all(np.asarray(cv) <= 0))
        x_opt = np.ravel(opt_result.X)
        p_evap_opt, dT_cd_opt = float(x_opt[0]), float(x_opt[1])

        # Re-solve at the exact optimum to unambiguously compute and store full KPI metrics
        model.solve_model(p_evap=p_evap_opt, dT_cd=dT_cd_opt)
        if is_feasible and model._solved:
            best_con = {k: model.get_parameter(k) for k in kpi}
            best_con["net_power"] = model.get_parameter("net_power")

    if best_con is None:
        valid = data[_feasible_mask(data, constraints)]
        if not valid.empty:
            print("\n  [i] res.X reported no feasible individual, but the log has "
                  f"{len(valid)} converged point(s) satisfying every constraint "
                  "-- using the best of those instead.")
            row = valid.loc[valid["net_power"].idxmax()]
            best_con = row.to_dict()

    if best_con is not None:
        print(f"\n--- Best (constrained, T_inj >= {T_inj_constraint:.2f} degC) ---")
        print(f"  p_evap      : {best_con['p_evap']:.3f} bar ({best_con['p_ratio_crit']:.2f} p_crit)")
        print(f"  dT_cd       : {best_con['dT_cd']:.2f} degC")
        print(f"  net power   : {best_con['net_power']:.2f} MW")
        print(f"  T_injection : {best_con['T_injection']:.2f} degC")
        print(f"  T_turb_in   : {best_con['T_turbine_in']:.2f} degC")
        print(f"  m_wf        : {best_con['m_workingfluid']:.1f} kg/s")
        print(f"  UA (steam)  : {best_con['evap_steam_UA']/1e3:.1f} kW/K")
        print(f"  UA (brine)  : {best_con['evap_brine_UA']/1e3:.1f} kW/K")
        print(f"  UA (preheat): {best_con['preheater_UA']/1e3:.1f} kW/K")
        print(f"  pinch (st)  : {best_con['evap_steam_pinch']:.2f} K (result)")
        print(f"  pinch (br)  : {best_con['evap_brine_pinch']:.2f} K (imposed)")
        print(f"  preheater   : ttd_min = {best_con['preheater_ttd_min']:.2f} K")
        print(f"  eta_th      : {best_con['thermal_efficiency']*100:.2f} %")
    else:
        print(f"\n  [!] No feasible point found with T_injection >= {T_inj_constraint:.2f} degC "
              f"(pymoo found no individual satisfying every constraint).")

    all_results[fluid] = {"log": data, "best_unconstrained": best_unc, "best_constrained": best_con}

    # Record the operating point that the diagram script will need
    chosen = best_con if best_con is not None else best_unc
    summary_rows.append({
        "fluid":           fluid,
        "cooling_fluid":   cooling_fluid,
        "T_geo":           T_geo,
        "m_geo":           m_geo,
        "x_steam":         x_steam,
        "T_amb":           T_amb,
        "P_amb":           P_amb,
        "dT_pp_evap":      dT_pp_evap,
        "dT_pp_cond":      dT_pp_cond,
        "dT_ap_pre":       dT_ap_pre,
        "p_evap_opt":      chosen["p_evap"],
        "p_ratio_crit":    chosen["p_ratio_crit"],
        "net_power_opt":   chosen["net_power"],
        "T_injection_opt": chosen["T_injection"],
        "thermal_efficiency": chosen["thermal_efficiency"],
        "constrained":     best_con is not None,
        "dT_cd":           chosen["dT_cd"],
    })

# -----------------------------------------------------------
# Summary Report
# -----------------------------------------------------------
print(f"\n{'='*90}")
print(f"{'SUMMARY - CONSTRAINED OPTIMUM PER FLUID':^90}")
print(f"{'='*90}")
print(f"{'Fluid':<15}{'p_opt [bar]':>13}{'p/p_crit':>10}{'dT_cd [C]':>11}"
      f"{'Net Power [MW]':>16}{'T_inj [C]':>11}{'Eta_th [%]':>12}")
print("-" * 90)

for fluid, res in all_results.items():
    bc = res.get("best_constrained")
    if bc is not None:
        print(f"{fluid:<15}{bc['p_evap']:>13.3f}{bc['p_ratio_crit']:>10.2f}"
              f"{bc['dT_cd']:>11.2f}{bc['net_power']:>16.2f}{bc['T_injection']:>11.2f}"f"{bc['thermal_efficiency']*100:>12.2f}")
    else:
        print(f"{fluid:<15}{'N/A':>13}{'N/A':>10}{'N/A':>11}{'N/A':>16}{'N/A':>11}{'N/A':>12}")

# Save the summary table needed by the diagram script
summary_df = pd.DataFrame(summary_rows)
summary_df.to_csv("optimal_points.csv", index=False)
print("\nSaved optimal_points.csv (read by HighEnthalpyGeoORC_Diagrams.py)")
