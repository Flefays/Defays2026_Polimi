# -*- coding: utf-8 -*-
"""
reCreated after the HDD data loss on Mon Mar  2 11:19:07 2026

@author: flori

This code aims to show a small example using a fan, a source, a sink and connections

"""

"---TESpy related imports---"

# Import the network object
from tespy.networks import Network

# Import respect.: the fluid components & fluid connections (+ Power if the reader want to use it)
from tespy.components import Source, Sink, Pump
from tespy.connections import Connection

"---Network definition---"

# Definition + disable/enable iteration informations
nw= Network(iterinfo = False)

# Change the default units
nw.units.set_defaults(temperature = 'degC', pressure = 'bar', enthalpy = 'kJ/kg', entropy = 'J/kgK', power = 'kW', heat = 'kW')

"---Components & Connections definition fluid side---"

su = Source('su')
ex = Sink('ex')
pp = Pump('fan')

c1 = Connection(su, 'out1', pp, 'in1', label = '1')
c2 = Connection(pp, 'out1', ex, 'in1', label = '2')

nw.add_conns(c1, c2)

c1.set_attr(p=1, T=25, m=300, fluid={'air': 1})
c2.set_attr(p = 1.05)
pp.set_attr(eta_s = 0.72)

nw.solve('design')
nw.print_results()
consommation = pp.P.val
print(f"Fan consumption : {consommation} kW,", f"s = {c1.s.val} J/(kg·K)")

