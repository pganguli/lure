from typing import TYPE_CHECKING

from lure.energy.energy_model import EnergyModelObserver
from lure.node.node_state import NodeState
if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode
from lure.node.net.ill.basic_ill import BasicILL
from lure.node.net.packet import Packet, PacketType
from lure.node.lmp.lmp import LMPConfigKey
from lure.node.power.threshold_power_supply import ThresholdPowerSupply

class GreedyClockILL(BasicILL):
    """An ILL that attempts to rendezvous between two nodes at the max of the estimated next time the nodes will be on."""

    HEADER_KEY_RENDEZVOUS = 'ill-rendezvous'
    HEADER_KEY_LAST_CALL = 'ill-last-call'

    def initialize(self, node: 'SensorNode'):
        super().initialize(node)
        self.harvester = node.power_supply.harvester
        self.power_supply: ThresholdPowerSupply = node.power_supply
        self.storage = node.power_supply.storage
        self.operating_discharge_rate = node.discharge_rates[NodeState.OPERATING]
        self.boot_time = node.os_boot_time_ms
        self.proposed_time_of_death = 0
        self.proposed_ttr = 0
        self.cutoff_ontime = self.power_supply.get_max_ontime_energy() / self.operating_discharge_rate * 0.75
        self.their_ttr = 0
        self.their_last_call = False

    def boot(self):
        super().boot()
        self.their_last_call = False
        self.their_ttr = 0
        self.proposed_time_of_death = 0
        self.proposed_ttr = 0

    def _time_to_rendezvous(self, time_til_off):
        current_energy = self.power_supply.get_current_energy() - min(time_til_off, self.power_supply.get_time_to_death(self.operating_discharge_rate)) * (self.operating_discharge_rate - self.harvester.get_next_charging_power())
        energy_at_off = self.storage.get_energy_for_voltage(self.power_supply.threshold_to_die_v)
        energy_at_on = self.storage.get_energy_for_voltage(self.power_supply.threshold_to_restart_v)
        # Need to use get_next_charging_power() here, not harvester.charging_power
        if self.harvester.get_next_charging_power() == 0:
            return -1

        # Calculate as if the node is turning off right now
        if current_energy >= energy_at_on:
            time_off = 0
        else:
            time_off = max((energy_at_on - current_energy) / self.harvester.get_next_charging_power(), 0)

        time_to_rendezvous = time_off + self.boot_time + 0.000001
        self.debug(f'time_to_rendezvous {time_to_rendezvous}, harvester {self.harvester.get_next_charging_power()}')
        return time_to_rendezvous

    def frame(self, packet: Packet) -> bool:
        self.debug(f'Framing {packet.type}')
        if packet.type is PacketType.ACK:
            time_til_death = 1
            my_ttr = self._time_to_rendezvous(time_til_death)
            if my_ttr >= 0 and self.their_ttr >= 0:
                time_to_rendezvous = max(my_ttr, self.their_ttr)
                self.debug(f'My ttr {my_ttr}, their ttr {self.their_ttr}')
                self.debug(f'Configuring LMP time to rendezvous to {time_to_rendezvous} (clock tick {self.time_module.time() + time_to_rendezvous})')
                packet.set_header(self.HEADER_KEY_RENDEZVOUS, time_to_rendezvous, 4)
                self.lmp.set_config(LMPConfigKey.OTHER, self.time_module.time() + time_to_rendezvous)
                last_call = self.time_module.clock() >= self.cutoff_ontime
                if self.their_last_call or last_call:
                    packet.set_header(self.HEADER_KEY_LAST_CALL, True, 1)
                    # Lock in LMP with value chosen when rendezvous was set
                    self.lmp.enable(lock=True)
                    self.debug(f'Locking in LMP. their_last_call {self.their_last_call}, mine {last_call}')
                else:
                    packet.set_header(self.HEADER_KEY_LAST_CALL, False, 1)
                        
            else:
                self.lmp.set_config(LMPConfigKey.OTHER, None)
                self.debug(f'Could not select a TTR (comparing {my_ttr} and {self.their_ttr})')
                return False
        else:
            time_til_death = self.netstack.slot_length + 1
            if self.time_module.clock() >= self.cutoff_ontime:
                packet.set_header(self.HEADER_KEY_LAST_CALL, True, 1)
            else:
                packet.set_header(self.HEADER_KEY_LAST_CALL, False, 1)
            self.proposed_time_of_death = self.time_module.clock() + time_til_death
            self.proposed_ttr = self._time_to_rendezvous(time_til_death)
            packet.set_header(self.HEADER_KEY_RENDEZVOUS, self.proposed_ttr, 4)
        return True

    def parse(self, packet: Packet) -> bool:
        self.debug(f'Parsing {packet.type}')
        
        if packet.type is PacketType.ACK:
            time_to_rendezvous = packet.get_header(self.HEADER_KEY_RENDEZVOUS)
            last_call = packet.get_header(self.HEADER_KEY_LAST_CALL)
            if time_to_rendezvous:
                self.debug(f'Configuring LMP time to rendezvous to {time_to_rendezvous} (clock tick {self.time_module.time() + time_to_rendezvous})')
                self.lmp.set_config(LMPConfigKey.OTHER, self.time_module.time() + time_to_rendezvous)
                if last_call:
                    self.lmp.enable(lock=True)
                    self.debug(f'Locking in LMP.')
                        
        else:
            self.their_ttr = packet.get_header(self.HEADER_KEY_RENDEZVOUS)
            self.their_last_call = packet.get_header(self.HEADER_KEY_LAST_CALL)

        return True

    def __str__(self):
        return f'GreedyClockILL'

class OracleClockILL(GreedyClockILL, EnergyModelObserver):
    """An ILL that attempts to rendezvous between two nodes at the max of the estimated next time the nodes will be on,
    and receives updates to this time when energy conditions change."""

    HEADER_KEY_RENDEZVOUS = 'ill-rendezvous'

    def initialize(self, node: 'SensorNode'):
        super().initialize(node)
        self.other_nodes = [n for n in node.simulation.nodes if n.node_id != node.node_id]
        node.simulation.energy_model.register_observer(self)

    def on_update(self):
        if self.lmp.get_config(LMPConfigKey.OTHER) is not None:
            my_ttr = self._time_to_rendezvous(0)
            their_ttr = self.other_nodes[0].netstack.ill._time_to_rendezvous(0)
            if my_ttr >= 0 and their_ttr >= 0:
                new_ttr = max(my_ttr, their_ttr)
                self.lmp.set_config(LMPConfigKey.OTHER, new_ttr + self.time_module.time())
                self.debug(f'Updated TTR to {new_ttr}')
            else:
                self.lmp.set_config(LMPConfigKey.OTHER, None)

    def __str__(self):
        return f'OracleClockILL'
            
