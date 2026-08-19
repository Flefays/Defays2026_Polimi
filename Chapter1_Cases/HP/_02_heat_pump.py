# -*- coding: utf-8 -*-
"""
Created on Tue Jul 21 16:25:12 2026

@author: flori

Write the Heat pump inside the ModelTemplate to conduct 
the optimization and exergy analysis as explained in latest version v0.10.2.

Add: (1) Build a power system in this purpose.
     (2) Condenser to MovingBoundaryHeatExchanger (Condenser not supported with exerpy => nan)

"""

import numpy as np
from CoolProp.CoolProp import PropsSI

from tespy.networks import Network
from tespy.components import (Compressor, MovingBoundaryHeatExchanger, Valve, HeatExchanger,CycleCloser, Source, Sink, PowerSource)
from tespy.connections import Connection, PowerConnection

from tespy.models import ModelTemplate


class HeatPumpModel(ModelTemplate):
    
    def __init__(self, WF,Tamb=10, pamb=1.013):
        self.WF = WF
        self.Tamb = Tamb
        self.pamb = pamb
        self._ean = None
        super().__init__()
        
    def _parameter_lookup(self):
        return {
            "T_evap": {"get": self.get_T_evap, "set": self.set_T_evap},
            "T_cond": {"get": self.get_T_cond, "set": self.set_T_cond},
            "COP": {"get": self.calc_cop},
            "pinch_condenser": {"get": self.calc_pinch_condenser},
            "T_discharge": ["Connections", "c1", "T"],
            "Q_cond": ["Components", "condenser", "Q"],
            "W_comp": ["Components", "compressor", "P"],
        }    
            
        
    def _create_network(self):
        
        # -----------------------------------------------------------
        # Network
        # -----------------------------------------------------------
        self.nw = Network()
        self.nw.iterinfo = False
        self.nw.units.set_defaults(temperature='degC', pressure='bar',
        pressure_difference="bar", enthalpy='kJ/kg')
        
        # -----------------------------------------------------------
        # Components
        # -----------------------------------------------------------
        cc = CycleCloser('cycle closer')
        comp = Compressor('compressor')
        cond = MovingBoundaryHeatExchanger('condenser')
        valve = Valve('expansion valve')
        evap = HeatExchanger('evaporator')
    
        so_src = Source('heat source source')
        si_src = Sink('heat source sink')
    
        so_sink = Source('heat sink source')
        si_sink = Sink('heat sink sink')
        
        elec = PowerSource('electricity grid')
        
        # -----------------------------------------------------------
        # Connections
        # -----------------------------------------------------------
        c0 = Connection(cc, 'out1', comp, 'in1', label='c0')
        c1 = Connection(comp, 'out1', cond, 'in1', label='c1')
        c2 = Connection(cond, 'out1', valve, 'in1', label='c2')
        c3 = Connection(valve, 'out1', evap, 'in2', label='c3')
        c4 = Connection(evap, 'out2', cc, 'in1', label='c4')
    
        self.nw.add_conns(c0, c1, c2, c3, c4)
    
        E1 = Connection(so_src, 'out1', evap, 'in1', label='E1')
        E2 = Connection(evap, 'out1', si_src, 'in1', label='E2')
        E4 = Connection(so_sink, 'out1', cond, 'in2', label='E4')
        E3 = Connection(cond, 'out2', si_sink, 'in1', label='E3')
    
        self.nw.add_conns(E1, E2, E4, E3)
        
        e0 = PowerConnection(elec, 'power', comp, 'power', label='e0')
        
        self.nw.add_conns(e0)
        
        # -----------------------------------------------------------
        # Parametrisation
        # -----------------------------------------------------------
        c2.set_attr(td_bubble=2)          # slightly subcooled liquid
        c4.set_attr(fluid={self.WF: 1}, td_dew=5)   # slightly superheated vapour

        # Heat source: 10 -> 7 degC
        E1.set_attr(fluid={'water': 1}, T=10, p=2)
        E2.set_attr(T=7)

        # Heat sink: 40 -> 45 degC
        E4.set_attr(fluid={'water': 1}, T=40, p=2, m=0.5)
        E3.set_attr(T=45)

        comp.set_attr(eta_s=0.75)
        cond.set_attr(pr1=0.98, pr2=0.98)
        evap.set_attr(pr1=0.98, pr2=0.98)

        # design-point saturation pressures from target saturation temperatures
        p_evap0 = PropsSI('P', 'T', 5 + 273.15, 'Q', 1, self.WF) / 1e5
        p_cond0 = PropsSI('P', 'T', 50 + 273.15, 'Q', 0, self.WF) / 1e5
        c4.set_attr(p=p_evap0)
        c2.set_attr(p=p_cond0)
        
        # Save objects to 'self' so they are accessible in other methods
        self.comp, self.cond, self.valve, self.evap, self.cc = comp, cond, valve, evap, cc
        self.c0, self.c1, self.c2, self.c3, self.c4 = c0, c1, c2, c3, c4
        self.E1, self.E2, self.E3, self.E4 = E1, E2, E3, E4

        self.nw.solve(mode='design')
        self._solved = self.nw.status == 0
        
    # -----------------------------------------------------------
    # Personnal set/get for the parameter lookup
    # -----------------------------------------------------------
    def _p_from_T_evap(self, T_evap):
        return PropsSI('P', 'T', T_evap + 273.15, 'Q', 1, self.WF) / 1e5

    def _p_from_T_cond(self, T_cond):
        return PropsSI('P', 'T', T_cond + 273.15, 'Q', 0, self.WF) / 1e5

    def set_T_evap(self, value):
        self.c4.set_attr(p=self._p_from_T_evap(value))

    def get_T_evap(self):
        p_pascal = self.c4.p.val * 1e5
        return PropsSI('T', 'P', p_pascal, 'Q', 1, self.WF) - 273.15

    def set_T_cond(self, value):
        self.c2.set_attr(p=self._p_from_T_cond(value))

    def get_T_cond(self):
        p_pascal = self.c2.p.val * 1e5
        return PropsSI('T', 'P', p_pascal, 'Q', 0, self.WF) - 273.15

    def calc_cop(self):
        if not self._solved:
            return np.nan
        return abs(self.cond.Q.val) / self.comp.P.val

    def calc_pinch_condenser(self):
        if not self._solved:
            return np.nan
        return min(self.cond.ttd_l.val, self.cond.ttd_u.val)
        
    def solve_model(self, **kwargs):
        self.solve_model_design(**kwargs)




