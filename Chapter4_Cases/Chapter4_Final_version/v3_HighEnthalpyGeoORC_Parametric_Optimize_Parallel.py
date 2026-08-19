# -*- coding: utf-8 -*-
"""
Created on Thu Aug  6 2026

@author: flori

PARAMETRIC OPTIMIZATION: Geothermal ORC Power Plant (High-Enthalpy Two-Phase Resource)

Description:
    Executes a parametric sweep and saves the outputs to a CSV file (subsequently 
    processed by HighEnthalpyGeoORC_parametric_diagrams.py):

    - T_geo sweep: For each working fluid and re-injection temperature constraint, 
      this script optimizes net power across a spectrum of geofluid temperatures (T_geo), 
      holding the steam fraction and dT_cd constant.
      -> results_Tgeo_sweep.csv

    Each individual optimization (n_fluid x n_T_geo x n_T_inj) represents a complete 
    pymoo execution (pop_size x n_gen evaluations) !!!
    
Update:
    The evaporation pressure bounds were updated based on the following relation:

        0.15 * p_crit <= p_evap <= min(0.90 * p_crit, p_sat(T_geo - dT_pp_evap - dT_margin))

AI USAGE:
    Previously, scripts executed each optimization run (n_fluid x n_T_geo x n_T_inj) sequentially. 
    AI was utilized as a assistance tool to refactor the workflow and enable parallel execution 
    of the pymoo optimizations.
    
    Because all pymoo runs are independent, the objective was to harness 3 out of 4 CPU cores 
    simultaneously. The AI suggested implementing `os.cpu_count()` to dynamically allocate 
    available core capacity across different machines.
    
    (+) Implementing Pymoo's native parallelization proved challenging due to its underlying 
    wrapper around TESPy. Consequently, 'ProcessPoolExecutor' was selected, and the AI helped 
    refine the concurrent execution pipeline for this script.
    
Note for students:
    Certain IDEs (such as Spyder) may encounter issues when attempting to interrupt multi-process 
    executions. If needed, active Python processes can be force-closed via the system Task Manager.
"""

import os
import numpy as np
import pandas as pd
from CoolProp.CoolProp import PropsSI as PSI
from concurrent.futures import ProcessPoolExecutor, as_completed
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


# -----------------------------------------------------------------------------
# Sweep settings (can be adjusted)
# -----------------------------------------------------------------------------
FLUIDS = ["n-Pentane", "Isopentane", "Cyclopentane", "n-Butane"]

T_geo_range = np.arange(140, 230 + 1, 10)     # 140, 150, ..., 230 °C
T_inj_values = [65, 75]                       # °C

x_steam_default = 0.1
m_geo = 180              # kg/s
cooling_fluid = "air"
T_amb = 15               # °C
P_amb = 0.6              # bar
dT_cd = 15               # °C  (fixed for this sweep)

dT_pp_evap = 10           # geobrine evaporator ttd_l 
dT_pp_cond = 10           # condenser td_pinch 
dT_ap_pre  = 5            # preheater outlet (approach point); x_r4 = 0 (for dT_ap_pre=0)    

termination = ("n_gen", 30)

# -----------------------------------------------------------------------------
# Optimisation routine for a single case
# -----------------------------------------------------------------------------
def optimize_case(fluid, T_geo, x_steam, T_inj):
    """
    Run an optimisation for a given fluid / T_geo / x_steam / T_inj.
    Returns a dict describing the result, or a dict with an "error" key
    if the case could not be evaluated.

    Note:
        
    - The DE algorithm instance is created HERE (not at module level) so
      nothing stateful is shared between worker processes.
    
    """
    algorithm = DE(pop_size=12)

    p_lo, p_hi = p_evap_bounds(fluid, T_geo, dT_pp_evap=dT_pp_evap)

    if p_hi <= p_lo:
        return {"fluid": fluid, "T_geo": T_geo, "T_inj": T_inj,
                "error": f"infeasible p_evap bounds (p_lo={p_lo:.2f} >= p_hi={p_hi:.2f})"}

    try:
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
        
    # Catches a hard exception from the initial "design" solve (not just _solved=False); skips this case without running DE.    
    except Exception as e:
        return {"fluid": fluid, "T_geo": T_geo, "T_inj": T_inj,
                "error": f"initial design solve failed: {e}"}
    
    # Variables, Constraints, Objectives, Tracking
    variables = {"p_evap":{"min": p_lo, "max": p_hi}}
    constraints = {"T_injection": {"min": T_inj}}
    objective = ["net_power"]
    minimize_flags = [False]     # maximise net_power
    kpi = ["T_injection", "p_evap", "p_ratio_crit", "T_turbine_in",
           "T_preheater_out", "m_workingfluid", "preheater_ttd_min",
           "evap_steam_pinch", "evap_brine_pinch",
           "evap_steam_UA", "evap_brine_UA", "thermal_efficiency"]

    try:
        log_df, res = model.optimize(
            algorithm=algorithm,
            termination=termination,
            variables=variables,
            constraints=constraints,
            objective=objective,
            minimize_flags=minimize_flags,
            kpi=kpi,
        )
    except Exception as e:
        return {"fluid": fluid, "T_geo": T_geo, "T_inj": T_inj,
                "error": f"optimisation failed: {e}"}

        finite = log_df.dropna(subset=["net_power"]) if log_df is not None else None

    # --- Same as what was done in Optimize ---
    """
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

    if res is not None and res.X is not None:
        cv = getattr(res, "CV", None)
        # If pymoo populates X, a missing CV implies the solution is feasible (CV <= 0)
        is_feasible = bool(cv is None or np.all(np.asarray(cv) <= 0))
        p_evap_opt = float(np.ravel(res.X)[0])
        net_power_opt = float(-np.ravel(res.F)[0])
        # Re-solve at the exact optimum to unambiguously compute and store full KPI metrics
        model.solve_model(p_evap=p_evap_opt, dT_cd=dT_cd)
        row = {k: model.get_parameter(k) for k in kpi} if model._solved else None
    elif finite is not None and not finite.empty:
        valid = finite[_feasible_mask(finite, constraints)]
        if not valid.empty:
            row = valid.loc[valid["net_power"].idxmax()]
            is_feasible = True
        else:
            # genuinely nothing in the log satisfies the constraint either
            row = finite.loc[finite["net_power"].idxmax()]
            is_feasible = False
        p_evap_opt = float(row["p_evap"])
        net_power_opt = float(row["net_power"])
        cv = None
    else:
        return {"fluid": fluid, "T_geo": T_geo, "T_inj": T_inj,
                "error": "no converged points at all"}

    def _kpi(name):
        return float(row[name]) if row is not None and name in row else np.nan

    return {
        "fluid": fluid, "T_inj": T_inj, "T_geo": T_geo,
        "x_steam": x_steam, "m_geo": m_geo,
        "cooling_fluid": cooling_fluid, "T_amb": T_amb, "P_amb": P_amb,
        "dT_cd": dT_cd,
        "dT_pp_evap": dT_pp_evap, "dT_pp_cond": dT_pp_cond,
        "dT_ap_pre": dT_ap_pre,
        "p_evap_opt": p_evap_opt,
        "net_power_opt": net_power_opt,
        "T_injection_opt": _kpi("T_injection"),
        "p_ratio_crit": _kpi("p_ratio_crit"),
        "T_turbine_in": _kpi("T_turbine_in"),
        "T_preheater_out": _kpi("T_preheater_out"),
        "m_workingfluid": _kpi("m_workingfluid"),
        "preheater_ttd_min": _kpi("preheater_ttd_min"),
        "evap_steam_pinch": _kpi("evap_steam_pinch"),
        "evap_brine_pinch": _kpi("evap_brine_pinch"),
        "thermal_efficiency": _kpi("thermal_efficiency"),
        "p_lo": p_lo, "p_hi": p_hi,
        "constrained": is_feasible,
        "CV": None if cv is None else float(np.ravel(cv)[0]),
    }


# -----------------------------------------------------------------------------
# Parallel sweep over (fluid, T_inj, T_geo)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    cases = [
        (fluid, float(T_geo), x_steam_default, T_inj)
        for fluid in FLUIDS
        for T_inj in T_inj_values
        for T_geo in T_geo_range
    ]
    n_cases = len(cases)

    # Leave one core free for the OS; adjust down further (e.g. //2)
    # if RAM becomes the bottleneck rather than CPU.
    n_workers = max(1, (os.cpu_count() or 2) - 1)
    print(f"Running {n_cases} cases on {n_workers} worker process(es)...")

    rows_Tgeo = []
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(optimize_case, *c): c for c in cases}

        for i, future in enumerate(as_completed(futures), 1):
            case = futures[future]
            try:
                result = future.result()
            except Exception as e:
                print(f"[{i}/{n_cases}] {case} crashed unexpectedly: {e}")
                continue

            if "error" in result:
                print(f"[{i}/{n_cases}] fluid={case[0]} T_geo={case[1]} "
                      f"T_inj={case[3]}: {result['error']}")
                continue

            flag = "" if result["constrained"] else "   [!] T_inj out of reach"
            print(f"[{i}/{n_cases}] fluid={case[0]} T_geo={case[1]} "
                  f"T_inj={case[3]}: net_power={result['net_power_opt']:.1f} "
                  f"p/p_crit={result['p_ratio_crit']:.2f} "
                  f"constrained={result['constrained']}{flag}")
            rows_Tgeo.append(result)

    pd.DataFrame(rows_Tgeo).to_csv("results_Tgeo_sweep.csv", index=False)
    print(f"\nSaved results_Tgeo_sweep.csv ({len(rows_Tgeo)}/{n_cases} cases succeeded)")
