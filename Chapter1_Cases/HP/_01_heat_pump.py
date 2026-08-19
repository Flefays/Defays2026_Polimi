# -*- coding: utf-8 -*-
"""
Created on Tue Jul 21 16:25:12 2026

@author: flori
"""

from tespy.networks import Network
from tespy.components import (Compressor, Condenser, Valve, HeatExchanger,CycleCloser, Source, Sink)
from tespy.connections import Connection
from CoolProp.CoolProp import PropsSI

WF    = {'R134a':1}
WATER = {'water':1}
FLUID = 'R134a'
# saturation pressures derived from target saturation temperatures (PropsSI)
p_evap_sat = PropsSI('P', 'T', 5 + 273.15, 'Q', 1, FLUID) / 1e5    # bar
p_cond_sat = PropsSI('P', 'T', 50 + 273.15, 'Q', 0, FLUID) / 1e5   # bar

# ---------------------------------------------------------------
# Network
# ---------------------------------------------------------------
nw = Network()
nw.units.set_defaults(temperature='degC', pressure='bar', enthalpy='kJ/kg')

# ---------------------------------------------------------------
# Components
# ---------------------------------------------------------------
cc = CycleCloser('cycle closer')

comp = Compressor('compressor')
cond = Condenser('condenser')
valve = Valve('expansion valve')
evap = HeatExchanger('evaporator')

# heat source (water loop)
so_src = Source('heat source source')
si_src = Sink('heat source sink')

# heat sink (water loop, e.g. domestic hot water)
so_sink = Source('heat sink source')
si_sink = Sink('heat sink sink')

# ---------------------------------------------------------------
# Connections 
# ---------------------------------------------------------------

# Working fluid cycle
c0 = Connection(cc, 'out1', comp, 'in1', label='c0')
c1 = Connection(comp, 'out1', cond, 'in1', label='c1')
c2 = Connection(cond, 'out1', valve, 'in1', label='c2')
c3 = Connection(valve, 'out1', evap, 'in2', label='c3')
c4 = Connection(evap, 'out2', cc, 'in1', label='c4')

nw.add_conns(c0, c1, c2, c3, c4)

# heat source water loop (evaporator primary side)
E1 = Connection(so_src, 'out1', evap, 'in1', label='E1')
E2 = Connection(evap, 'out1', si_src, 'in1', label='E2')

# heat sink water loop (condenser secondary side)
E4 = Connection(so_sink, 'out1', cond, 'in2', label='E4')
E3 = Connection(cond, 'out2', si_sink, 'in1', label='E3')


nw.add_conns(E1, E2, E4, E3)

# ---------------------------------------------------------------
# Parametrisation
# ---------------------------------------------------------------

# WF Connections
c2.set_attr(p=p_cond_sat, td_bubble=2)   # slightly subcooled liquid
c4.set_attr(fluid=WF, td_dew=5, p=p_evap_sat) # slightly superheated vapour

# Heat Source Connections: 10 -> 7 degC
E1.set_attr(fluid=WATER, T=10, p=2)
E2.set_attr(T=7)

# Heat Sink Connections: 40 -> 45 degC
E4.set_attr(fluid=WATER, T=40, p=2, m=0.5)
E3.set_attr(T=45)

# Components
comp.set_attr(eta_s=0.75)                             
cond.set_attr(pr1=0.98, pr2=0.98, subcooling=True)   
evap.set_attr(pr1=0.98, pr2=0.98)

# ---------------------------------------------------------------
# Solve
# ---------------------------------------------------------------
nw.solve(mode='design')
nw.print_results()

Q_cond = cond.Q.val
W_comp = comp.P.val
COP = abs(Q_cond) / W_comp
print(f"\nHeating capacity Q_cond = {Q_cond/1e3:.2f} kW")
print(f"Compressor power   W_cp = {W_comp/1e3:.2f} kW")
print(f"COP (heating)          = {COP:.2f}")

# ---------------------------------------------------------------
# fluprodia
# ---------------------------------------------------------------

# Custom script to import and plot fluprodia diagrams as desired (Mine)
from Fluprodia_diagrams_f import plot_TS_diagram, plot_TH_diagram, plot_Clapeyron_diagram, plot_Molier_diagram, plot_logPh_diagram, save_plots

# Build the data dictionary
dico = {
    
    "compressor": nw.get_comp('compressor').get_plotting_data()[1],
    "condenser": nw.get_comp('condenser').get_plotting_data()[1],
    "valve": nw.get_comp('expansion valve').get_plotting_data()[1],
    "evaporator": nw.get_comp('evaporator').get_plotting_data()[2],
}

# Cal of plotting functions
figures = {}
fig, name = plot_TS_diagram(FLUID, dico)
figures[name] = fig
fig, name = plot_TH_diagram(FLUID, dico)
figures[name] = fig
fig, name = plot_Clapeyron_diagram(FLUID, dico)
figures[name] = fig
fig, name = plot_Molier_diagram(FLUID, dico)
figures[name] = fig
fig, name = plot_logPh_diagram(FLUID, dico)
figures[name] = fig

# Plot saves
save_plots(figures)





