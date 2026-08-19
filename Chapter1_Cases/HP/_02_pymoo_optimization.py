# -*- coding: utf-8 -*-
"""
Created on Tue Jul 21 20:48:33 2026

@author: flori

Goal: find the evaporation/condensation saturation temperatures that
maximise the heating COP, subject to a constraint (a maximum compressor discharge
temperature)

Design variables : T_evap [deg°C], T_cond [deg°C]
Objective        : maximise COP
Constraint       : T_discharge <= T_discharge_max

"""

from pymoo.algorithms.soo.nonconvex.de import DE

from _02_heat_pump import HeatPumpModel


for WF in ["R134a"]: # Allow to do the calculation for multiple working fluid

    hp = HeatPumpModel(WF)
    hp.nw.print_results()
    print(f"\nCOP = {hp.get_parameter('COP'):.3f}")
    print(f"T_evap = {hp.get_parameter('T_evap'):.2f} degC")
    print(f"T_cond = {hp.get_parameter('T_cond'):.2f} degC")
    hp.save_design()


    log, res = hp.optimize(
        algorithm=DE(pop_size=20),          
        termination=("n_gen", 10),
        variables={
            "T_evap": {"min": -10, "max": 4},
            "T_cond": {"min": 46, "max": 65},
        },
        constraints={
            "T_discharge": {"max": 100},      # degC, compressor outlet limit
            "pinch_condenser": {"min": 0},    # no temperature cross
        },
        objective=["COP"],
        minimize_flags=[False],               # maximise COP
        kpi=["T_discharge", "pinch_condenser"],
    )
    
    print(log)
    
    # result.X / result.F already contain only feasible solutions
    print("\nBest design point found:")
    print(f"  T_evap = {res.X[0]:.2f} degC")
    print(f"  T_cond = {res.X[1]:.2f} degC")
    print(f"  COP    = {-res.F[0]:.3f}")   # res.F is the internally minimized (negated) objective







