from lure.config.configuration import Config
from lure.node.net.packet import Packet, PacketType
from lure.node.net.network.network import Network
from lure.node.sensor_node import SensorNode
from lure.node.stats import StatType
import simpy
from typing import List


class SingleHopNetwork(Network):
    """Establishes a network topology where all nodes neighbor one another"""

    def __init__(self, config: Config):
        super().__init__(config)
        self.routes = {}

    def initialize(self, node: SensorNode, simpy_env: simpy.core.Environment):
        """Initialize with the simulation. Establish what the network neighbors are.

        :param node: The node this protocol belongs to
        :type node: SensorNode
        :param simpy_env: The environment this simulation takes place in
        :type simpy_env: simpy.core.Environment
        """
        super().initialize(node, simpy_env)
        neighbors = self.get_net_neighbors(node)
        for n in neighbors:
            self.routes[n] = n
            self.stats.list_append(StatType.NETWORK_NEIGHBORS, n)

    def get_next_hop(self, packet: Packet) -> int:
        """Retrieve the next hop ID based upon the desintation ID of the packet

        :param packet: The packet to be sent
        :type packet: Packet
        :return: The node_id the packet should be sent to next
        :rtype: int
        """
        super().get_next_hop(packet)
        if packet.type == PacketType.CONTROL:
            return self.netstack.BROADCAST_ADDRESS
        return packet.destination_id

    def get_net_neighbors(self, node: SensorNode) -> List[int]:
        """Retrieve all network neighbors of this node

        :param node: This node
        :type node: SensorNode
        :return: A list of all node_id's of network neighbors
        :rtype: List[int]
        """
        neighbors = []
        other_nodes = [
            n.node_id for n in node.simulation.nodes if n.node_id != self.node_id
        ]
        neighbors = other_nodes
        return neighbors
