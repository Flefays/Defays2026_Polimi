# -*- coding: utf-8 -*-
"""
reCreated after the HDD data loss on Thu Mar  5 18:09:28 2026

@author: flori

This code aims to do an ORC with a preheater and a recuperator in a Subsystem class from TESPy

- Fluid & Power to determine if the input/output method has limitation.

- Has to be called on a test case as a component.

"""

"---TESpy related imports---"

# Fluid & Power related
from tespy.components import Subsystem, HeatExchanger, MovingBoundaryHeatExchanger, Pump, Turbine, CycleCloser
from tespy.components import PowerBus, PowerSink, Motor, Generator
from tespy.connections import Connection, PowerConnection

#%%  ---Building the power network following the physical flow chart---

class ORC_1a(Subsystem):
    "---Class documentation---"
    def __init__(self, label):
        self.num_in = 3
        self.num_out = 3
        super().__init__(label)

    def create_network(self):
        "---Define the subsystem's components & connections---"
        
        # Cycle Components
        cc = CycleCloser('cc')
        turb = Turbine('turbine')
        recup = HeatExchanger('recup')
        cond = MovingBoundaryHeatExchanger('cond')
        pp = Pump('pump')
        preh = HeatExchanger('preheater')
        evap = HeatExchanger('evap')
        
        # Hot Soucre Connections
        h0 = Connection(self.inlet, 'out1',evap, 'in1', label = 'h0')
        h1 = Connection(evap, 'out1', preh, 'in1', label = 'h1')
        h2 = Connection(preh, 'out1', self.outlet, 'in1', label = 'h2')
        
        # Add to the subsystem those connections
        self.add_conns(h0, h1, h2)
        
        # Cycle Fluid Connections
        c0 = Connection(evap, 'out2', cc, 'in1', label = 'c0')
        c1 = Connection(cc, 'out1', turb, 'in1', label = 'c1')
        c2 = Connection(turb, 'out1', recup, 'in1', label = 'c2')
        c3 = Connection(recup, 'out1', cond, 'in1', label = 'c3')
        c4 = Connection(cond, 'out1', pp, 'in1', label = 'c4')
        c5 = Connection(pp, 'out1', recup, 'in2', label = 'c5')
        c6 = Connection(recup, 'out2', preh, 'in2', label = 'c6')
        c7 = Connection(preh, 'out2', evap, 'in2', label = 'c7')
        
        # Add to the subsystem those connections
        self.add_conns(c0, c1, c2, c3, c4, c5, c6, c7)
        
        # Cold Sink Connections
        i0 = Connection(self.inlet, 'out2', cond, 'in2', label = 'w0')
        i1 = Connection(cond, 'out2', self.outlet, 'in2', label = 'w1')
        
        # Add to the subsystem those connections
        self.add_conns(i0, i1)
        
        # Power Component
        ORC_bus1 = PowerBus('electricity bus of the ORC 1', num_in = 1, num_out = 2)
        ORC_bus2 = PowerBus('electricity bus of the ORC 2', num_in = 2, num_out = 1)
        pp_mot = Motor('pump motor')
        turb_gen = Generator('Turbine generator')
        
        # Power Connections
        e0 = PowerConnection(turb, 'power', turb_gen, 'power_in', label = 'e0')
        e1 = PowerConnection(turb_gen, 'power_out', ORC_bus1, 'power_in1', label = 'e1')
        e2 = PowerConnection(ORC_bus1, 'power_out1', self.outlet, 'in3', label = 'e2')
        e3 = PowerConnection(ORC_bus1, 'power_out2', ORC_bus2, 'power_in1', label = 'e3')
        e4 = PowerConnection(ORC_bus2, 'power_out1', pp_mot, 'power_in', label = 'e4')
        e5 = PowerConnection(pp_mot, 'power_out', pp, 'power', label = 'e5')
        e6 = PowerConnection(self.inlet, 'out3', ORC_bus2, 'power_in2', label = 'e6')
        
        # Add to the subsystem those connections
        self.add_conns(e0, e1, e2, e3, e4, e5, e6)
     
#%% ---Using only one PowerBus to do an internal balance and reinject the surplus---
       
class ORC_1b(Subsystem):
    "---Class documentation---"
    def __init__(self, label):
        self.num_in = 2
        self.num_out = 2
        super().__init__(label)

    def create_network(self):
        "---Define the subsystem's components & connections---"
        
        # Cycle Components
        cc = CycleCloser('cc')
        turb = Turbine('turbine')
        recup = HeatExchanger('recup')
        cond = MovingBoundaryHeatExchanger('cond')
        pp = Pump('pump')
        preh = HeatExchanger('preheater')
        evap = HeatExchanger('evap')
        
        # Hot Soucre Connections
        h0 = Connection(self.inlet, 'out1',evap, 'in1', label = 'h0')
        h1 = Connection(evap, 'out1', preh, 'in1', label = 'h1')
        h2 = Connection(preh, 'out1', self.outlet, 'in1', label = 'h2')
        
        # Add to the subsystem those connections
        self.add_conns(h0, h1, h2)
        
        # Cycle Fluid Connections
        c0 = Connection(evap, 'out2', cc, 'in1', label = 'c0')
        c1 = Connection(cc, 'out1', turb, 'in1', label = 'c1')
        c2 = Connection(turb, 'out1', recup, 'in1', label = 'c2')
        c3 = Connection(recup, 'out1', cond, 'in1', label = 'c3')
        c4 = Connection(cond, 'out1', pp, 'in1', label = 'c4')
        c5 = Connection(pp, 'out1', recup, 'in2', label = 'c5')
        c6 = Connection(recup, 'out2', preh, 'in2', label = 'c6')
        c7 = Connection(preh, 'out2', evap, 'in2', label = 'c7')
        
        # Add to the subsystem those connections
        self.add_conns(c0, c1, c2, c3, c4, c5, c6, c7)
        
        # Cold Sink Connections
        i0 = Connection(self.inlet, 'out2', cond, 'in2', label = 'w0')
        i1 = Connection(cond, 'out2', self.outlet, 'in2', label = 'w1')
        
        # Add to the subsystem those connections
        self.add_conns(i0, i1)
        
        # Power Component
        "(BUS: the power is generated from the turbine [num_in = 1] & sent to the pump motor + the grid [num_out = 2])"
        Turboden_ORC_bus = PowerBus('electricity bus of the ORC', num_in = 1, num_out = 2)
        Turboden_ORC_grid = PowerSink('grid connection of the ORC')
        motor = Motor('feed pump motor')
        generator = Generator('turbine linked alternator')
       
        # Power connections PowerConnection(source, outlet_id, target, inlet_id, kwargs)
        e1 = PowerConnection(turb, 'power', generator, 'power_in', label='e1')
        e2 = PowerConnection(generator, 'power_out', Turboden_ORC_bus, 'power_in1', label='e2')
        e3 = PowerConnection(Turboden_ORC_bus, 'power_out1', motor, 'power_in', label='e3')
        e4 = PowerConnection(motor, 'power_out', pp, 'power', label='e4')
        e5 = PowerConnection(Turboden_ORC_bus, 'power_out2', Turboden_ORC_grid, 'power', label='e5')
       
        # Add those connections to the class'network
        self.add_conns(e1, e2, e3, e4, e5)
        
        
        
        
        
        
        
        
        
        
        
        