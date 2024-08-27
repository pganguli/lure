
from typing import List, TYPE_CHECKING
import simpy
if TYPE_CHECKING:
    from lure.node.net.mac.mac import MAC
    from lure.node.net.ill.ill import ILL
    from lure.node.net.network.network import Network
    from lure.node.net.physical.physical import Physical
    from lure.node.sensor_node import SensorNode
from lure.config.configuration import Config
from lure.node.net.packet import Framer, Packet
from lure.node.stats import Stats, StatsProvider


class Netstack(StatsProvider):
    """The netstack belonging to a single node. Is a StatsProvider.
    """
    BROADCAST_ADDRESS = -1

    def __init__(self, config: Config):
        self.addr = None
        self.slot_length = None
        config.extract("slot_length", self, 5)

        self.mac: 'MAC' = Config.instantiate_from_dict(config.config["mac"], 'lure.node.net.mac')
        self.ill: 'ILL' = Config.instantiate_from_dict(config.config["ill"], 'lure.node.net.ill')
        self.network: 'Network' = Config.instantiate_from_dict(config.config["network"], 'lure.node.net.network')
        self.physical: 'Physical' = Config.instantiate_from_dict(config.config["physical"], 'lure.node.net.physical')

        self.framers: List[Framer] = []

    def initialize(self, node: 'SensorNode', all_netstacks: List['Netstack'], simpy_env: simpy.core.Environment):
        """Initializes with the simulation. Calls initialize() on the ILL, MAC, NETWORK, and PHYSICAL layers. Adds framers.

        :param node: The SensorNode object that this netstack belongs to
        :type node: SensorNode
        :param all_netstacks: All netstacks present in the simulation
        :type all_netstacks: List[&#39;Netstack&#39;]
        :param simpy_env: The simpy environment used for stat time tracking. Is observational in this class and all subclasses
        :type simpy_env: simpy.core.Environment
        """
        # self.addr = node.node_id
        self.ill.initialize(node)
        self.mac.initialize(node)
        self.network.initialize(node, simpy_env)
        self.physical.initialize(node, all_netstacks)

        self.framers.append(node.lmp)
        self.framers.append(node.time_module)
        self.framers.append(self.ill)

    def frame(self, packet: Packet) -> bool:
        """Frames a packet

        :param packet: Packet to be framed
        :type packet: Packet
        :return: Boolean for a successful framing
        :rtype: bool
        """
        packet.framed = True
        headers_added = False
        for f in self.framers:
            headers_added |= f.frame(packet)
        return headers_added

    def parse(self, packet: Packet) -> bool:
        """Parses a framed packet

        :param packet: Packet to be parsed
        :type packet: Packet
        :return: Boolean for a successful parse
        :rtype: bool
        """
        parsed = False
        for f in self.framers:
            parsed |= f.parse(packet)
        return parsed

    def boot(self):
        """Called by SensorNode. Calls boot() on all network layers.
        """
        self.mac.boot()
        self.ill.boot()
        self.network.boot()
        self.physical.boot()

    def execute(self):
        """Executes on every simulation tick that this node is on for. Calls execute() on each network layer.
        """
        self.mac.execute()
        self.ill.execute()
        self.network.execute()
        self.physical.execute()

    def set_addr(self, addr):
        """Sets the netstack address.

        :param addr: The new address for this netstack
        """
        self.addr = addr

    def __str__(self):
        return f'slot-{self.slot_length}_mac-{self.mac}_ill-{self.ill}'

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.ill.stats = stats
        self.mac.stats = stats
        self.network.stats = stats
        self.physical.stats = stats
