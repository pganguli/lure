from typing import TYPE_CHECKING
from ....energy.energy_model import EnergyModelObserver

from lure.node.node_state import NodeState
if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode
from lure.node.net.ill.basic_ill import BasicILL
from lure.node.net.packet import Packet
from lure.node.lmp.lmp import LMPConfigKey

class SIGreedyILL(BasicILL):
    """A soft intermittent ILL that chooses the max of the estimated next wake time for two nodes to rendezvous."""

    HEADER_KEY_RENDEZVOUS = 'ill-rendezvous'

    def initialize(self, node: 'SensorNode'):
        super().initialize(node)
        self.harvester = node.power_supply.harvester
        self.storage = node.power_supply.storage
        self.power_supply = node.power_supply
        self.operating_discharge_rate = node.discharge_rates[NodeState.OPERATING]
        self.sleeping_discharge_rate = node.discharge_rates[NodeState.SLEEPING]
        self._node = node

    def _time_to_rendezvous(self):
        current_energy = self.power_supply.get_current_energy()
        energy_at_sleep = self.storage.get_energy_for_voltage(self.lmp.get_config(LMPConfigKey.SLEEP_THRESHOLD))
        energy_at_wake = self.storage.get_energy_for_voltage(self.lmp.get_config(LMPConfigKey.WAKE_THRESHOLD))
        # Need to use get_next_charging_power() here, not harvester.charging_power
        if self._node.state is NodeState.OPERATING:
            time_til_sleep = max((current_energy - energy_at_sleep) / (self.operating_discharge_rate - self.harvester.get_next_charging_power()), 0)
        else:
            time_til_sleep = 0
        if self.harvester.get_next_charging_power() <= self.sleeping_discharge_rate:
            return -1
        if self._node.state is NodeState.SLEEPING:
            if current_energy >= energy_at_wake:
                time_asleep = 0
            else:
                time_asleep = max((energy_at_wake - current_energy) / (self.harvester.get_next_charging_power() - self.sleeping_discharge_rate), 0)
        else:
            time_asleep = max((energy_at_wake - energy_at_sleep) / (self.harvester.get_next_charging_power() - self.sleeping_discharge_rate), 0)
        time_to_rendezvous = time_til_sleep + time_asleep
        self.debug(f'time_til_sleep {time_til_sleep}, time_asleep {time_asleep}, time_to_rendezvous {time_to_rendezvous}, harvester {self.harvester.charging_power}, discharge {self.sleeping_discharge_rate}')
        return time_to_rendezvous

    def frame(self, packet: Packet) -> bool:
        packet.set_header(self.HEADER_KEY_RENDEZVOUS, self._time_to_rendezvous(), 4)
        return True

    def parse(self, packet: Packet) -> bool:
        my_ttr = self._time_to_rendezvous()
        their_ttr = packet.get_header(self.HEADER_KEY_RENDEZVOUS)
        if my_ttr >= 0 and their_ttr >= 0:
            time_to_rendezvous = max(my_ttr, their_ttr)
            self.debug(f'Configuring LMP time to rendezvous to {time_to_rendezvous} (clock tick {self.time_module.clock() + time_to_rendezvous})')
            self.lmp.set_config(LMPConfigKey.OTHER, self.time_module.clock() + time_to_rendezvous)
        else:
            self.lmp.set_config(LMPConfigKey.OTHER, None)
            self.debug(f'Could not select a TTR (comparing {my_ttr} and {their_ttr})')
        return True

    def __str__(self):
        return f'SIGreedyILL'

class SIOracleILL(SIGreedyILL, EnergyModelObserver):
    """A soft intermittent ILL that receives updates to the rendezvous time when the energy model updates."""


    HEADER_KEY_RENDEZVOUS = 'ill-rendezvous'

    def initialize(self, node: 'SensorNode'):
        super().initialize(node)
        self.other_nodes = [n for n in node.simulation.nodes if n.node_id != node.node_id]
        node.simulation.energy_model.register_observer(self)

    def on_update(self):
        if self.lmp.get_config(LMPConfigKey.OTHER) is not None:
            my_ttr = self._time_to_rendezvous()
            their_ttr = self.other_nodes[0].netstack.ill._time_to_rendezvous()
            if my_ttr >= 0 and their_ttr >= 0:
                new_ttr = max(my_ttr, their_ttr)
                self.lmp.set_config(LMPConfigKey.OTHER, new_ttr + self.time_module.clock())
                self.debug(f'Updated TTR to {new_ttr}')
            else:
                self.lmp.set_config(LMPConfigKey.OTHER, None)

    def __str__(self):
        return f'SIOracleILL'
            
