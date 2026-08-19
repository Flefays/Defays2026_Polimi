# -*- coding: utf-8 -*-
"""
Created on Mon Jun  1 13:11:29 2026 (revised)

@author: flori

MODEL TEMPLATE: Geothermal ORC Power Plant (High-Enthalpy Two-Phase Resource)

Description:
    Topological network of an Organic Rankine Cycle (ORC) power plant driven
    by high-enthalpy geothermal fluid. Conducting only subcritical cycles:
    the turbine inlet is always saturated vapour.
    
Note:
    Drum removed (originally a numerical convenience, but potentially useful in other designs).
    Parameters updated relative to previous version marked by "drum compensation".
    
    Added p_crit values to compute the ratio: p = p_evap / p_crit

    (!) The preheater outlet (r4) set the approach using the temperature difference 
    to bubble line, or x = 0 if the approach is set to 0 (exactly the bubble point).
    The td_bubble from TESPy works fine with p_evap variations induced 
    in the optimizations. 
    
    This approach follows the same logic as Chen et al., "Parametric optimization 
    and comparative study of an organic Rankine cycle power plant for two-phase 
    geothermal sources" (preheater approach: tb_bp = -2; see thesis references).
  
Free Specifications:
    - Working Fluid & Cooling Fluid
    - Geofluid Temperature, flowrate & vapour fraction 
    (!) The latter may be limited by the specifications of the heat exchangers.
    - Working Fluid evaporation pressure 
    - Cooling dT
    - Pinches (condenser td_pinch, geobrine evaporator ttd_l) and preheater
      approach (dT_ap_preh)

Fixed Specifications:
    - Pressure drops
    - Cooling Temperatures & pressures
    - Some other state variables
"""

from CoolProp.CoolProp import PropsSI as PSI

from tespy.components import (
    CycleCloser, Generator, Motor, MovingBoundaryHeatExchanger, HeatExchanger,
    PowerBus, PowerSink, Pump, Sink, Source, Turbine, DropletSeparator,
    Merge, Splitter
)
from tespy.connections import Connection, PowerConnection, Ref
from tespy.models import ModelTemplate
from tespy.networks import Network


class HighEnthalpyGeoORC(ModelTemplate):

    def __init__(self, working_fluid, cooling_fluid, geofluidTemperature,
                 geofluidFlow, geofluidVapour, evaporationPressure,
                 T_amb, P_amb, dT_cd, dT_pp_evap=10, dT_pp_cond=10, dT_ap_pre=0):
        self.working_fluid = working_fluid   # ex: ('Isopentane', 'n-Butane')
        self.cooling_fluid = cooling_fluid   # ex: ('air', 'water')
        self.geo_T = geofluidTemperature
        self.geo_m = geofluidFlow
        self.steam_x = geofluidVapour
        self.p_evap = evaporationPressure
        self.T_amb = T_amb
        self.P_amb = P_amb
        self.dT_cd = dT_cd
        self.dT_pp_evap = dT_pp_evap   # geobrine evaporator ttd_l (10°C by default)
        self.dT_pp_cond = dT_pp_cond   # condenser td_pinch (10°C by default)
        self.dT_ap_pre = dT_ap_pre     # preheater outlet approach (0 by default)
        self.p_crit = PSI('Pcrit', working_fluid) / 1e5      # bar
        self.T_crit = PSI('Tcrit', working_fluid) - 273.15   # degC
        super().__init__()

    def _parameter_lookup(self) -> dict:
        # Export any component or connection value of interest here. (see TESPy returned values)
        return {
            "evap_steam_UA": ["Components", "geosteam evaporator", "UA"],
            "evap_brine_UA": ["Components", "geobrine evaporator", "UA"],
            "preheater_UA": ["Components", "preheater", "UA"],
            # evap brine pinch ttd_l imposed, ttd_min = min(ttd_u,ttd_l)
            "evap_steam_pinch": ["Components", "geosteam evaporator", "ttd_min"],
            "evap_brine_pinch": ["Components", "geobrine evaporator", "ttd_l"],
            "condenser_pinch": ["Components", "condenser", "td_pinch"],
            "preheater_ttd_min": ["Components", "preheater", "ttd_min"],
            "net_power": ["Connections", "e6", "E"],
            "T_geofluid": ["Connections", "f0", "T"],
            "T_injection": ["Connections", "f6", "T"],
            "T_turbine_in": ["Connections", "r0", "T"],
            "T_preheater_out": ["Connections", "r4", "T"],
            "m_geofluid": ["Connections", "f0", "m"],
            "m_workingfluid": ["Connections", "r0", "m"],
            "p_evap": ["Connections", "r0", "p"],
            "p_ratio_crit": {
                "get": lambda: self.nw.get_conn("r0").p.val / self.p_crit
            },
            "dT_cd": {
                "get": lambda: self.nw.get_conn("a2").T.val - self.T_amb,
                "set": lambda val: self.nw.get_conn("a2").set_attr(T=self.T_amb + val),
            },
            "thermal_efficiency": {"get": self.thermal_efficiency},
        }

    def _create_network(self) -> None:
        super()._create_network()

        # -----------------------------------------------------------
        # Network
        # -----------------------------------------------------------
        self.nw = Network(iterinfo=False)
        self.nw.units.set_defaults(
            temperature = "degC", pressure = "bar",
            pressure_difference = "bar", power = "MW",
            heat = "kW", enthalpy = "kJ/kg"
        )

        # -----------------------------------------------------------
        # Components
        # -----------------------------------------------------------
        # Sources and Sinks
        geo_fluid = Source('geofluid')
        geo_reinjection = Sink('re-injection')

        air_in = Source('air source')
        air_out = Sink('air sink')

        # Main components
        turbine = Turbine("turbine")
        condenser = MovingBoundaryHeatExchanger("condenser")
        pump = Pump("pump")
        air_fan = Pump('air fan')
        preheater = HeatExchanger("preheater")
        orc_cc = CycleCloser('cycle closer of ORC')

        geofluid_separator = DropletSeparator('Separator')
        evap_splitter = Splitter('splitter before evaporators')
        evap_merge = Merge('merge after evaporators')
        evap_steam = HeatExchanger('geosteam evaporator')
        evap_brine = HeatExchanger('geobrine evaporator')
        geofluid_merge = Merge('merge condensate & brine')

        # Power components
        generator = Generator("generator")
        motor1 = Motor("motor1")
        motor2 = Motor("motor2")
        power_bus = PowerBus("bus", num_in=1, num_out=3)
        grid = PowerSink("grid")

        # -----------------------------------------------------------
        # Connections 
        # -----------------------------------------------------------
        f0 = Connection(geo_fluid, 'out1', geofluid_separator, 'in1', label='f0')
        f1 = Connection(geofluid_separator, 'out2', evap_steam, 'in1', label='f1')
        f2 = Connection(geofluid_separator, 'out1', evap_brine, 'in1', label='f2')
        f3 = Connection(evap_steam, 'out1', geofluid_merge, 'in1', label='f3')
        f4 = Connection(evap_brine, 'out1', geofluid_merge, 'in2', label='f4')
        f5 = Connection(geofluid_merge, 'out1', preheater, 'in1', label='f5')
        f6 = Connection(preheater, 'out1', geo_reinjection, 'in1', label='f6')

        r0 = Connection(orc_cc, 'out1', turbine, 'in1', label='r0')
        r1 = Connection(turbine, 'out1', condenser, 'in1', label='r1')
        r2 = Connection(condenser, 'out1', pump, 'in1', label='r2')
        r3 = Connection(pump, 'out1', preheater, 'in2', label='r3')
        r4 = Connection(preheater, 'out2', evap_splitter, 'in1', label='r4')
        r5 = Connection(evap_splitter, 'out1', evap_steam, 'in2', label='r5')
        r6 = Connection(evap_splitter, 'out2', evap_brine, 'in2', label='r6')
        r7 = Connection(evap_steam, 'out2', evap_merge, 'in1', label='r7')
        r8 = Connection(evap_brine, 'out2', evap_merge, 'in2', label='r8')
        r9 = Connection(evap_merge, 'out1', orc_cc, 'in1', label='r9')

        a0 = Connection(air_in, 'out1', air_fan, 'in1', label='a0')
        a1 = Connection(air_fan, 'out1', condenser, 'in2', label='a1')
        a2 = Connection(condenser, 'out2', air_out, 'in1', label='a2')

        self.nw.add_conns(f0, f1, f2, f3, f4, f5, f6, r0, r1, r2, r3, r4, r5, r6, r7, r8, r9, a0, a1, a2)

        # Power Connections
        e0 = PowerConnection(turbine, "power", generator, "power_in", label="e0")
        e1 = PowerConnection(generator, "power_out", power_bus, "power_in1", label="e1")
        e2 = PowerConnection(power_bus, "power_out1", motor1, "power_in", label="e2")
        e3 = PowerConnection(motor1, "power_out", pump, "power", label="e3")
        e4 = PowerConnection(power_bus, "power_out2", motor2, "power_in", label="e4")
        e5 = PowerConnection(motor2, "power_out", air_fan, "power", label="e5")
        e6 = PowerConnection(power_bus, "power_out3", grid, "power", label="e6")

        self.nw.add_conns(e0, e1, e2, e3, e4, e5, e6)

        # -----------------------------------------------------------
        # Parametrisation
        # -----------------------------------------------------------
        # fluid settings
        f0.set_attr(fluid={'water': 1.0})
        r0.set_attr(fluid={self.working_fluid: 1.0})
        a0.set_attr(fluid={self.cooling_fluid: 1.0})

        
        # Evaporation pressure & turbine inlet (Optimization Variable)
        r0.set_attr(p=self.p_evap, x=1, m0=50) # Saturated vapour (subcritical only)

        # Geofluid
        geo_massflow = self.geo_m; steam_share = self.steam_x
        p_f0 = PSI('P', 'T', self.geo_T + 273.15, 'Q', steam_share, 'water') / 1e5 # bar
        f0.set_attr(m=geo_massflow, T=self.geo_T, x=steam_share)
        f3.set_attr(x=0) # Condensate 

        # Cooling fluid
        a0.set_attr(T=self.T_amb, p=self.P_amb, m0=3000)
        a2.set_attr(T=self.T_amb + self.dT_cd, p=self.P_amb)

        # Turbine and pumps
        turbine.set_attr(eta_s=0.90)
        pump.set_attr(eta_s=0.75)
        air_fan.set_attr(eta_s=0.60)

        # Pressure Ratios or Pressure Drops
        condenser.set_attr(pr1=1, pr2=0.998)
        preheater.set_attr(pr1=0.99, pr2=0.99)
        evap_steam.set_attr(pr2=1)     # pr2 fixed here (drum compensation); pr1 from evap_brine
        evap_brine.set_attr(pr1=0.99)  # pr2 follows from evap_steam with splitter/merge equality

        # Additional ones
        r2.set_attr(x=0) # Condenser outlet
        
        # Preheater outlet (r4): approach point
        if self.dT_ap_pre == 0:
            r4.set_attr(x=0)
        else:
            r4.set_attr(td_bubble=self.dT_ap_pre)

        # Parallel Branches => Full vaporization at the same enthalpy (drum compensation)
        r8.set_attr(h=Ref(r7, 1, 0))

        # Pinches
        evap_brine.set_attr(ttd_l=self.dT_pp_evap)
        condenser.set_attr(td_pinch=self.dT_pp_cond)

        # Initial Pressure Conditions
        f1.set_attr(p0=p_f0)
        f2.set_attr(p0=p_f0)

        # Electric efficiencies
        generator.set_attr(eta=1)
        motor1.set_attr(eta=1)
        motor2.set_attr(eta=1)

        self.nw.solve("design")
        self._solved = self.nw.status == 0
        #NB: self.nw.print_results() => connections 

    def solve_model(self, **kwargs):
        self.solve_model_design(**kwargs)

    def get_parameter(self, parameter: str):
        """
        A failed solve (nw.status != 0, or an exception caught
        in solve_model) does NOT leave NaN in the connections by default.
        
        """
        if not getattr(self, "_solved", True):
            return float("nan")
        return super().get_parameter(parameter)

    # -----------------------------------------------------------
    # Personnal set/get for the parameter lookup
    # -----------------------------------------------------------
    def thermal_efficiency(self):
        """
        Net thermal efficiency of the ORC: eta_net = W_net / Q_in
        
        """
        preheater = self.nw.get_comp('preheater')
        evap_steam = self.nw.get_comp('geosteam evaporator')
        evap_brine = self.nw.get_comp('geobrine evaporator')

        Q_in = abs(preheater.Q.val) + abs(evap_steam.Q.val) + abs(evap_brine.Q.val)
        W_net_plant = abs(self.nw.get_conn('e6').E.val) * 1000

        return W_net_plant / Q_in
