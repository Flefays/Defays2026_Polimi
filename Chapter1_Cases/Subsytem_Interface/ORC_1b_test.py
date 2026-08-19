# -*- coding: utf-8 -*-
"""
Created on Thu Mar  5 20:45:03 2026

@author: flori

This code test the ORC_1b (ORC Subsystem) and plot the Ts diagram from my personal functions using fluprodia.

"""
#%% --- Imports---

"---Class 1b Import---"

# Path (Have to be complete if the file locations are not linked) 
import sys
sys.path.append(r'D:\codes\functions')

# Class import
from ORC_preheat_recup_Subsyst_f import ORC_1b
from Fluprodia_diagrams_f import plot_TS_diagram, save_plots

"---Standard imports---"

# CoolProp to extract fluid properties
from CoolProp.CoolProp import PropsSI as PSI

"---TESpy related imports---"

# Import the network object
from tespy.networks import Network

# Import the fluid and power components and connections 
from tespy.components import Source, Sink, Pump
from tespy.components import PowerBus,PowerSource, Motor
from tespy.connections import Connection, PowerConnection

#%% ---Common Fluid Network---

"---Network definition---"

# Definition + disable/enable iteration informations
nw = Network(iterinfo = False)

# Change the default units
nw.units.set_defaults(temperature = 'degC', pressure = 'bar', enthalpy = 'kJ/kg', entropy = 'J/kgK', power = 'kW', heat = 'kW')

"---ORC Subsystem---"

# Import ORC_1b "component"
ORC = ORC_1b('ORC Subsytem')

# Add the subsystem to the network
nw.add_subsystems(ORC)

"---Water system component and connections (Fluid)---"

# Components
w_su = Source('water suction')
w_pp = Pump('water feed pump')
w_ex = Sink('water exhaust')

# Connections
w0 = Connection(w_su, 'out1', w_pp, 'in1', label = 'w0')
w1 = Connection(w_pp, 'out1', ORC, 'in1', label = 'w1')
w2 = Connection(ORC, 'out1', w_ex, 'in1', label = 'w2')

# Add to the network
nw.add_conns(w0, w1, w2)

"---Air system component and connections (Fluid)---"

# Components
a_su = Source('air suction')
a_pp = Pump('air fan')
a_ex = Sink('air exhaust')

# Connections
a0 = Connection(a_su, 'out1', a_pp, 'in1', label = 'a0')
a1 = Connection(a_pp, 'out1', ORC, 'in2', label = 'a1')
a2 = Connection(ORC, 'out2', a_ex, 'in1', label = 'a2')

# Add to the network
nw.add_conns(a0, a1, a2)

#%% ---Power network for ORC_1b---

"---Create an independent external network (link with the ORC internal network later by the results only)---"

# Components
grid_in = PowerSource('Supply from the grid')
nw_bus = PowerBus('network bus', num_in = 1, num_out = 2)
a_motor = Motor('air fan motor')
w_motor = Motor('water pump motor')

# Connections
nw_e0b = PowerConnection(grid_in, 'power', nw_bus, 'power_in1', label = 'e0b')   # If Correct, this line result has to be compute with the net power result from ORC_1b ('e5')
nw_e1b = PowerConnection(nw_bus, 'power_out1', a_motor, 'power_in', label = 'e1b')
nw_e2b = PowerConnection(nw_bus, 'power_out2', w_motor, 'power_in', label = 'e2b')
nw_e3b = PowerConnection(a_motor, 'power_out', a_pp, 'power', label = 'e3b')
nw_e4b = PowerConnection(w_motor, 'power_out', w_pp, 'power', label = 'e4b')

# Add connections
nw.add_conns(nw_e0b, nw_e1b, nw_e2b, nw_e3b, nw_e4b)

#%% ---Parametrisation for ORC_1b---

"---Adaptation of the I. Tuschy & F. Witte parametrisation from an ORC code---"

# Fluids
in1_fluid = {'water': 1}
working_fluid = "Isopentane"
in2_fluid = {'air': 1}

# Get the working cycle pressures from CoolProp.PropsSI (T are Kelvin and P are Pa inside CoolProp !)
p_high = PSI("P", "T", 140 + 273.15, "Q", 1, working_fluid) / 1e5 # from quality and T => P in Pa => bar
p_low = PSI("P", "T", 50 + 273.15, "Q", 1, working_fluid) / 1e5   # from quality and T => P in Pa => bar

# Attribute parameters at connections 
w0.set_attr(fluid= in1_fluid, p=10, T=160, m=100)
a0.set_attr(fluid= in2_fluid, p=1, T=20)
a2.set_attr(T= 35)

ORC.get_conn('h1').set_attr(h0 = 140)
ORC.get_conn('c1').set_attr(fluid={working_fluid: 1}, x=1, T= 140) # saturated gas at evap/cc outlet, turbine entrance
ORC.get_conn('c3').set_attr(p0=p_low)
ORC.get_conn('c4').set_attr(x=0) # saturated liquid at condenser outlet, pump entrance
ORC.get_conn('c7').set_attr(x=0, p0=p_high) # saturated liquid at preheater outlet

# Attribute parameters at components
ORC.get_comp('recup').set_attr(pr1 = 1, pr2 = 1, eff_hot=0.5) # no pressure drops assumption
ORC.get_comp('preheater').set_attr(pr1 = 1, pr2 = 1) # no pressure drops assumption
ORC.get_comp('cond').set_attr(pr1 = 1, pr2 = 1, td_pinch= 5) # no pressure drops assumption
ORC.get_comp('evap').set_attr(pr1 = 1, pr2 = 1, ttd_l = 5) # no pressure drops assumption
ORC.get_comp('turbine').set_attr(eta_s = 0.85)
ORC.get_comp('pump').set_attr(eta_s = 0.75)

# Attribute electrical parameters at components
ORC.get_comp('feed pump motor').set_attr(eta=0.97) 
ORC.get_comp('turbine linked alternator').set_attr(eta=0.97) 

"---For the added feed water pump and the air fan---"

# To have no incidence from those pumps
w_pp.set_attr(pr = 1, eta_s = 1)
a_pp.set_attr(pr = 1, eta_s = 1)

# Attribute electrical parameters at components
w_motor.set_attr(eta= 0.97) 
a_motor.set_attr(eta= 0.97) 

nw.solve('design')
nw.print_results()


#%% ---Ts diagram---

dico = {
 "Turbine" : ORC.get_comp('turbine').get_plotting_data()[1],

"Condenser": ORC.get_comp('cond').get_plotting_data()[1],

"Pump": ORC.get_comp('pump').get_plotting_data()[1],

"Preheater": ORC.get_comp('preheater').get_plotting_data()[2],

"evaporator": ORC.get_comp('evap').get_plotting_data()[2],

"Recuperator (hot side)": ORC.get_comp('recup').get_plotting_data()[1],

"Recuperator (cold side)": ORC.get_comp('recup').get_plotting_data()[2],
}

figures = {}

fig, name = plot_TS_diagram(working_fluid, dico)
figures[name] = fig

save_plots(figures)

#%% ---System net power ?---

"---Net power calculation---"

# ORC net power
production = ORC.get_conn('e5').E.val
print(f"ORC production without auxiliaries: {production} kW ")

# Auxiliaries consumptions (2 ways to determine the same value IF eta = 1)
consumption1 = a_pp.P.val + w_pp.P.val ; consumption2 = nw_e0b.E.val # E for power connections not P
print(f" aux. cons. method 1: {consumption1} kW", f"aux. cons. method 2: {consumption2} kW")

"""
This 2 values are not equals since I used eta = 0.97 in the power network 
simulating mechanical efficiencies between the electricity fed 
to the pump motors vs the true pump power.
"""

# System net power
Net = production - consumption2
print(f"Net output power: {Net} kW")

#%% --- Parameter Study: Turbine Inlet Temperature ---

import matplotlib.pyplot as plt

T_hot_out_range = []
orc_power_range = []
system_net_power_range = []
T_turbine_in_range = [150, 140, 130, 120, 110, 100, 90, 80]

for T in T_turbine_in_range:
    # Update the turbine inlet temperature
    ORC.get_conn('c1').set_attr(T=T)
    
    # Resolve the network
    nw.solve("design")
    
    # Collect results
    T_hot_out_range.append(w2.T.val)
    
    orc_net = ORC.get_conn('e5').E.val
    sys_net = orc_net - nw_e0b.E.val
    
    orc_power_range.append(orc_net)
    system_net_power_range.append(sys_net)

# --- Plotting the Results ---

fig, ax = plt.subplots(2, sharex=True, figsize=(8, 6))

# Top Plot: Heat source outflow temperature
ax[0].plot(T_turbine_in_range, T_hot_out_range, color='purple', linestyle='--')
ax[0].set_ylabel("Re-injection temp (°C)")
ax[0].grid(True)

# Bottom Plot: Power Comparison (2 lines)
ax[1].plot(T_turbine_in_range, orc_power_range, color='blue', label="ORC Net Power")
ax[1].plot(T_turbine_in_range, system_net_power_range, color='orange', label="System Net Power")
ax[1].set_ylabel("Power (kW)")
ax[1].set_xlabel("Turbine inlet temperature (°C)")
ax[1].legend(loc="best")
ax[1].grid(True)

plt.tight_layout()
# --- Save Graph as SVG ---
plt.savefig("1st_parametric_study.svg", format="svg", bbox_inches="tight")
plt.show()







