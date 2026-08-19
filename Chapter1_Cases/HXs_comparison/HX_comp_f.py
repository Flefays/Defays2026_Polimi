# -*- coding: utf-8 -*-
"""
reCreated after the HDD data loss on Mon Mar  2 11:46:16 2026

@author: flori

This code aims to display HXs diagrams to validate the method, based on the test case in TESPy documentation

"""

"---Function Imports---"

# Path (Have to be complete if the file locations are not linked) 
import sys
sys.path.append(r'D:\codes\functions')

# Functions import
from HX_diagrams_f import plot_tq_HX, plot_tq_CD, plot_tq_MBHX_SHX

"---TESpy related imports---"

# Import the network object
from tespy.networks import Network

# Import respect.: the fluid components & fluid connections
from tespy.components import Source, Sink, Condenser, HeatExchanger, MovingBoundaryHeatExchanger, SectionedHeatExchanger
from tespy.connections import Connection

"---Network definition---"

# Definition + disable/enable iteration informations
nw= Network(iterinfo = False)

# Change the default units
nw.units.set_defaults(temperature = 'degC', pressure = 'bar', enthalpy = 'kJ/kg', entropy = 'J/kgK', power = 'kW', heat = 'kW')

"---Components & Connections definition fluid side---"

# Hot side & Cold side, sources & sinks
h_su = Source('h_su')
h_ex = Sink('h_ex')
c_su = Source('c_su')
c_ex = Sink('c_ex')

# --- CHOOSE YOUR HEAT EXCHANGER HERE ---
hx_type = 'CD' # Options: 'CD', 'HX', 'MBHX', 'SHX'

if hx_type == 'CD':
    hx = Condenser('CD')
elif hx_type == 'HX':
    hx = HeatExchanger('HX')
elif hx_type == 'MBHX':
    hx = MovingBoundaryHeatExchanger('MBHX')
elif hx_type == 'SHX':
    hx = SectionedHeatExchanger('SHX')
else:
    raise ValueError("Invalid hx_type selected.")

# Connections on both sides (hot & cold)
c1 = Connection(h_su, 'out1', hx, 'in1', label = '1')
c2 = Connection(hx, 'out1', h_ex, 'in1', label = '2')
d1 = Connection(c_su, 'out1', hx, 'in2', label = '3')
d2 = Connection(hx, 'out2', c_ex, 'in1', label = '4')

nw.add_conns(c1, c2, d1, d2)

"---BCs from documentation---"

# On the connections
c1.set_attr(m = 5, T_dew = 60, td_dew = 50, fluid = {'R290':1})
c2.set_attr(td_bubble = 5)
d1.set_attr(T = 45, p = 1, fluid = {'water':1})
d2.set_attr(T = 55)

# On the component 
if hx_type == 'CD':
    hx.set_attr(dp1=0, dp2=0, subcooling=True) 
elif hx_type == 'SHX':
    hx.set_attr(dp1=0, dp2=0, num_sections=10)
else:
    hx.set_attr(dp1=0, dp2=0) # For HX and MBHX

nw.solve('design')
nw.print_results()

"---Call the diagram functions---"

# The heat exchanger diagrams  
if hx_type == 'CD':
    plot_tq_CD(hx, 'Condenser')
elif hx_type == 'HX':
    plot_tq_HX(hx, 'HeatExchanger')
elif hx_type == 'MBHX':
    plot_tq_MBHX_SHX(hx, 'MovingBoundaryHeatExchanger')
elif hx_type == 'SHX':
    plot_tq_MBHX_SHX(hx, 'SectionedHeatExchanger (10 sections)')
    
#%% Previous parametrization
"""
The following parametrization was working, but, I changed it to use subcooling = True in the Condenser

"""

"""
c1.set_attr(m = 5, T_dew = 60,  T = 60 + 50,  fluid = {'R290':1})
c2.set_attr(T = 60 - 5)
d1.set_attr(T = 45, p = 1, fluid = {'water':1})
d2.set_attr(T = 55)

hx.set_attr(dp2 = 0) # dp2 = 0 condenser; dp1 & dp2 = 0 HX, MBHX and SHX (+ num_sections = choice)
"""

#%% ---Supercritical Region---

"---General imports---"

# Matplotlib to create 4 figures in one.
import matplotlib.pyplot as plt

"---TESpy related imports---"

# Import the network object
from tespy.networks import Network

# Import respect.: the fluid components & fluid connections
from tespy.components import Source, Sink, SectionedHeatExchanger
from tespy.connections import Connection

"---Network definition---"

# Definition + disable/enable iteration informations
nw= Network(iterinfo = False)

# Change the default units
nw.units.set_defaults(temperature = 'degC', pressure = 'bar', enthalpy = 'kJ/kg', entropy = 'J/kgK', power = 'kW', heat = 'kW')

"---Components & Connections definition fluid side---"

# Hot side & Cold side, sources & sinks
h_su = Source('h_su')
h_ex = Sink('h_ex')
c_su = Source('c_su')
c_ex = Sink('c_ex')

# The heat exchanger 
hx = SectionedHeatExchanger('SHX')

# Connections on both sides (hot & cold)
c1 = Connection(h_su, 'out1', hx, 'in1', label = '1')
c2 = Connection(hx, 'out1', h_ex, 'in1', label = '2')
d1 = Connection(c_su, 'out1', hx, 'in2', label = '3')
d2 = Connection(hx, 'out2', c_ex, 'in1', label = '4')

nw.add_conns(c1, c2, d1, d2)

"---BCs in supercritical region---"

# Parameterization for supercritical R290 (Pcrit ~ 42.5 bar)
c1.set_attr(m = 5, p = 50, T = 130, fluid = {'R290': 1})
c2.set_attr(T = 40)
d1.set_attr(T = 30, p = 5, fluid = {'water': 1})
d2.set_attr(T = 110)

# On the component
hx.set_attr(dp1 = 0, dp2 = 0) # num_sections will be updated in a loop to conduct a sensitivity study

"---Superposition Graph Creation---"

sections_to_test = [1, 2, 10, 50]
fig, ax = plt.subplots(figsize=(10, 6))

# Define colors for the hot side in the 4 tests
colors = ['red', 'green', 'orange', 'purple']

for i, n in enumerate(sections_to_test):
    hx.set_attr(num_sections = n)
    nw.solve('design')
    
    # Extract plotting data using the TESPy embedded function for SHX & MBHX
    heat, T_hot, T_cold, heat_per_section, td_log_per_section = hx.calc_sections()
    
    # Conversion to kW  and Celsius if previous to v0.9.16
    heat_kw = heat
    T_hot_C = T_hot
    T_cold_C = T_cold 
    
    # Plot cold side but only once (since it must remain the same, just to improve the visual)
    if i == 0:
        ax.plot(heat_kw, T_cold_C, "o-", color="blue", linewidth=2, label="Cold Side (Water)")
    else:
        ax.plot(heat_kw, T_cold_C, "-", color="blue", linewidth=2)

    # Plotting hot side for the 4 tests
    ax.plot(heat_kw, T_hot_C, "o-", color=colors[i], label=f"Hot Side (n={n})")

ax.set_title("Supercritical R290 T-Q Diagram: Discretisation Sensitivity", fontsize=18)
ax.set_ylabel("Temperature in °C", fontsize=18)
ax.set_xlabel("Cumulative Heat Transferred in kW", fontsize=18)
ax.legend(fontsize=16)
ax.grid(True, linestyle='--', alpha=0.6)
ax.tick_params(axis='both', which='major', labelsize=14)
plt.tight_layout()

# Save in SVG
plt.savefig("SHX_Superposition_R290.svg", format='svg', bbox_inches='tight')
plt.show()