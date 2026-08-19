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

import numpy as np
from CoolProp.CoolProp import PropsSI

# HP builder imports
from tespy.networks import Network
from tespy.components import (Compressor, Condenser, Valve, HeatExchanger, CycleCloser, Source, Sink)
from tespy.connections import Connection

# Optimization Imports
from pymoo.optimize import minimize
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.soo.nonconvex.de import DE

WF    = {'R134a':1}
WATER = {'water':1}
FLUID = 'R134a'
T_DISCHARGE_MAX = 100 + 273.15   # [K] compressor outlet temperature limit

def build_network():
    """reBuild the heat pump network. The parameters are updated per call."""
    nw = Network(iterinfo=False)
    nw.units.set_defaults(temperature='degC', pressure='bar', enthalpy='kJ/kg')

    cc = CycleCloser('cycle closer')
    comp = Compressor('compressor')
    cond = Condenser('condenser')
    valve = Valve('expansion valve')
    evap = HeatExchanger('evaporator')

    so_src = Source('heat source source')
    si_src = Sink('heat source sink')

    so_sink = Source('heat sink source')
    si_sink = Sink('heat sink sink')

    c0 = Connection(cc, 'out1', comp, 'in1', label='c0')
    c1 = Connection(comp, 'out1', cond, 'in1', label='c1')
    c2 = Connection(cond, 'out1', valve, 'in1', label='c2')
    c3 = Connection(valve, 'out1', evap, 'in2', label='c3')
    c4 = Connection(evap, 'out2', cc, 'in1', label='c4')

    nw.add_conns(c0, c1, c2, c3, c4)

    E1 = Connection(so_src, 'out1', evap, 'in1', label='E1')
    E2 = Connection(evap, 'out1', si_src, 'in1', label='E2')

    E4 = Connection(so_sink, 'out1', cond, 'in2', label='E4')
    E3 = Connection(cond, 'out2', si_sink, 'in1', label='E3')

    nw.add_conns(E1, E2, E4, E3)
    
    c2.set_attr(td_bubble=2)   
    c4.set_attr(fluid=WF, td_dew=5) 

    E1.set_attr(fluid=WATER, T=10, p=2)
    E2.set_attr(T=7)

    E4.set_attr(fluid=WATER, T=40, p=2, m=0.5)
    E3.set_attr(T=45)

    comp.set_attr(eta_s=0.75)                             
    cond.set_attr(pr1=0.98, pr2=0.98, subcooling=True)   
    evap.set_attr(pr1=0.98, pr2=0.98)

    return nw, dict(c0=c0, c1=c1, c2=c2, c4=c4, comp=comp, cond=cond)

nw, conns = build_network()

class HeatPumpProblem(ElementwiseProblem):

    def __init__(self):
        """ 
         T_evap must stay below the source outlet (7 degC) and
         T_cond must stay above the sink outlet (45 degC),
         otherwise the heat exchanger pinch would be violated.
        """
        super().__init__(
            n_var=2, n_obj=1, n_constr=2,
            xl=np.array([-10, 46]),    # [T_evap_min, T_cond_min] 
            xu=np.array([4, 65]),      # [T_evap_max, T_cond_max] 
        )

    def _evaluate(self, x, out, *args, **kwargs):
        T_evap, T_cond = x

        p_evap = PropsSI('P', 'T', T_evap + 273.15, 'Q', 1, FLUID) / 1e5
        p_cond = PropsSI('P', 'T', T_cond + 273.15, 'Q', 0, FLUID) / 1e5

        conns['c4'].set_attr(p=p_evap)
        conns['c2'].set_attr(p=p_cond)

        try:
            nw.solve(mode='design', init_only=False)
            if not nw.converged:
                raise RuntimeError('not converged')
            COP = abs(conns['cond'].Q.val) / conns['comp'].P.val
            T_discharge = conns['c1'].T.val + 273.15
            pinch_violation = -min(conns['cond'].ttd_l.val, conns['cond'].ttd_u.val)
        except Exception:
            out["F"] = [1e3]       # heavy penalty if the model fails to solve
            out["G"] = [1e3, 1e3]
            return

        out["F"] = [-COP]
        out["G"] = [
            T_discharge - T_DISCHARGE_MAX,   # <= 0: discharge temp constraint
            pinch_violation,                 # <= 0: no temperature cross in the condenser
        ]


if __name__ == '__main__':
    problem = HeatPumpProblem()
    algorithm = DE(pop_size=20)   

    res = minimize(problem, algorithm, ('n_gen', 10)) # , seed=1, verbose=True could be used.

    print("\nBest design point found:")
    print(f"  T_evap = {res.X[0]:.2f} degC")
    print(f"  T_cond = {res.X[1]:.2f} degC")
    print(f"  COP    = {-res.F[0]:.3f}")










