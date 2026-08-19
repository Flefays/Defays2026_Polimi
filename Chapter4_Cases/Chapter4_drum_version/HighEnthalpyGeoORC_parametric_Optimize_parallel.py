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
from concurrent.futures import ProcessPoolExecutor, as_completed
from CoolProp.CoolProp import PropsSI as PSI
from pymoo.algorithms.soo.nonconvex.de import DE

from HighEnthalpyGeoORC_Template import HighEnthalpyGeoORC

# -----------------------------------------------------------------------------
# Sweep settings (can be adjusted)
# -----------------------------------------------------------------------------
FLUIDS = ["n-Pentane", "Isopentane", "Cyclopentane", "n-Butane"]

T_geo_range = np.arange(150, 230 + 1, 10)     # 180, 190, ..., 250 °C
T_inj_values = [70, 100]                      # °C

x_steam_default = 0.1    
m_geo = 180              # kg/s
cooling_fluid = "air"
T_amb = 15               # °C
P_amb = 0.6              # bar
dT_cd = 20               # °C   (fixed for this sweep)

termination = ("n_gen", 20)

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

    p_crit = PSI('Pcrit', fluid) / 1e5          # bar
    t_crit = PSI('Tcrit', fluid) - 273.15       # °C
    t_max_evap = min(T_geo - 10, t_crit - 15)   # keep a margin (subcritical)
    t_min_evap = 50

    p_evap = PSI('P', 'T', (t_max_evap + 273.15), 'Q', 1, fluid) / 1e5

    try:
        model = HighEnthalpyGeoORC(
            working_fluid=fluid,
            cooling_fluid=cooling_fluid,
            geofluidTemperature=T_geo,
            geofluidFlow=m_geo,
            geofluidVapour=x_steam,
            evaporationPressure=p_evap,
            T_amb=T_amb,
            P_amb=P_amb,
            dT_cd=dT_cd,
        )
        
    # Catches a hard exception from the initial "design" solve (not just _solved=False); skips this case without running DE.    
    except Exception as e:
        return {"fluid": fluid, "T_geo": T_geo, "T_inj": T_inj,
                "error": f"initial design solve failed: {e}"}

    p_max_calc = PSI('P', 'T', t_max_evap + 273.15, 'Q', 1, fluid) / 1e5  # bar
    p_min_calc = PSI('P', 'T', t_min_evap + 273.15, 'Q', 1, fluid) / 1e5  # bar
    p_hi = min(p_max_calc, 0.90 * p_crit)
    p_lo = max(p_min_calc, 1.05)

    if p_hi <= p_lo:
        return {"fluid": fluid, "T_geo": T_geo, "T_inj": T_inj,
                "error": f"infeasible p_evap bounds (p_lo={p_lo:.2f} >= p_hi={p_hi:.2f})"}
    
    # Variables, Constraints, Objectives, Tracking
    variables = {"p_evap": {"min": float(round(p_lo, 2)), "max": float(round(p_hi, 2))}}
    constraints = {"T_injection": {"min": T_inj}}
    objective = ["net_power"]
    minimize_flags = [False]     # maximise net_power
    kpi = ["T_injection", "p_evap"]

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

    if res is None or res.X is None:
        # no individual could be evaluated successfully at all
        return {"fluid": fluid, "T_geo": T_geo, "T_inj": T_inj,
                "error": "no converged points at all"}

    # CV = total constraint violation (verification)
    cv = getattr(res, "CV", None)
    is_feasible = bool(cv is not None and np.all(np.asarray(cv) <= 0))

    p_evap_opt = float(np.ravel(res.X)[0])
    # Maximize = Minimize the opposite => res.F < 0
    net_power_opt = float(-np.ravel(res.F)[0])

    # T_injection is a constraint, not part of res, => log_df
    T_injection_opt = float(
        log_df.loc[np.isclose(log_df["p_evap"], p_evap_opt, atol=1e-3), "T_injection"].iloc[0]
    )

    return {
        "fluid": fluid, "T_inj": T_inj, "T_geo": T_geo,
        "x_steam": x_steam, "m_geo": m_geo,
        "cooling_fluid": cooling_fluid, "T_amb": T_amb, "P_amb": P_amb,
        "p_evap_opt": p_evap_opt,
        "net_power_opt": net_power_opt,
        "T_injection_opt": T_injection_opt,
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

            print(f"[{i}/{n_cases}] fluid={case[0]} T_geo={case[1]} "
                  f"T_inj={case[3]}: net_power={result['net_power_opt']:.1f} "
                  f"constrained={result['constrained']}")
            rows_Tgeo.append(result)

    pd.DataFrame(rows_Tgeo).to_csv("results_Tgeo_sweep.csv", index=False)
    print(f"\nSaved results_Tgeo_sweep.csv ({len(rows_Tgeo)}/{n_cases} cases succeeded)")