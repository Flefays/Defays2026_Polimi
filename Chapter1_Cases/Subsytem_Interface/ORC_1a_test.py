# -*- coding: utf-8 -*-
"""
Created on Thu Mar  5 20:45:03 2026

@author: flori

This code aims to show the invalidity in building power connections in the same way as fluid connections

"""

"---Class 1a Import---"

# Path (Have to be complete if the file locations are not linked) 
import sys
sys.path.append(r'D:\codes\functions')

# Class import
from ORC_preheat_recup_Subsyst_f import ORC_1a


"---TESpy related imports---"

# Import the network object
from tespy.networks import Network

# Import the fluid and power components and connections 
from tespy.components import Source, Sink, Pump
from tespy.components import PowerBus,PowerSource, PowerSink, Motor
from tespy.connections import Connection, PowerConnection

"---Network definition---"

# Definition + disable/enable iteration informations
nw = Network(iterinfo = False)

# Change the default units
nw.units.set_defaults(temperature = 'degC', pressure = 'bar', enthalpy = 'kJ/kg', entropy = 'J/kgK', power = 'kW', heat = 'kW')

"---ORC Subsystem---"

# ORC_1a class import
ORC = ORC_1a('ORC Subsytem')

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

"---Construction of an external power network and link it to the ORC internal Power network---"

# Components
grid_in = PowerSource('Supply from the grid')
grid_out = PowerSink('injection on the grid')
nw_bus = PowerBus('network bus', num_in = 1, num_out = 3)
a_motor = Motor('air fan motor')
w_motor = Motor('water pump motor')

# Connections
nw_e0a = PowerConnection(grid_in, 'power', nw_bus, 'power_in1', label = 'e0a')
nw_e1a = PowerConnection(nw_bus, 'power_out1', a_motor, 'power_in', label = 'e1a')
nw_e2a = PowerConnection(nw_bus, 'power_out2', w_motor, 'power_in', label = 'e2a')
nw_e3a = PowerConnection(nw_bus, 'power_out3', ORC, 'in3', label = 'e3a')
nw_e4a = PowerConnection(a_motor, 'power_out', a_pp, 'power', label = 'e4a')
nw_e5a = PowerConnection(w_motor, 'power_out', w_pp, 'power', label = 'e5a')
nw_e6a = PowerConnection(ORC, 'out3',grid_out,'power', label = 'e6a')  # If Correct, this line will be the net power of the overall system

# Add connections
nw.add_conns(nw_e0a, nw_e1a, nw_e2a, nw_e3a, nw_e4a, nw_e5a, nw_e6a)

"""
Even without parametrisation, just by running this code in3/out3 for 
power connections are not recognized.

ValueError: Error creating connection. 
Specified connector for ORC Subsytem_outlet of class SubsystemInterface (in3)  
is not available. Select one of the following connectors .

PS: power_in3/power_out3 are not existing, and adding a simple 
self.inlet to self.outlet connection in the subsystem class for 
the fluid could allow the reader to see in3/out3 works for fluid connections 
as it is built that way in TESPy

"""