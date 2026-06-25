from lure.config.configuration import Config
from lure.node.net.packet import Packet, PacketType
from lure.node.net.network.network import Network
from lure.node.sensor_node import SensorNode
from typing import List
import simpy
from lure.node.stats import StatType


class StaticNetwork(Network):
    """Establish a topology configured by static routes defined by configuration"""

    def __init__(self, config: Config):
        super().__init__(config)
        self.routes = None
        config.extract("routes", self, None)

    def initialize(self, node: SensorNode, simpy_env: simpy.core.Environment):
        """Initialization with simulation

        :param node: SensorNode object that this subclass belongs to
        :type node: SensorNode
        :param simpy_env: The simpy environment that is used for time stamping statistics
        :type simpy_env: simpy.core.Environment
        """
        super().initialize(node, simpy_env)
        neighbors = self.get_net_neighbors()
        for n in neighbors:
            self.stats.list_append(StatType.NETWORK_NEIGHBORS, n)

    def get_next_hop(self, packet: Packet) -> int:
        """Retrieves the packets next hop node by comparing its destination_id with its preset next hop table

        :param packet: A packet to be forwarded to another node
        :type packet: Packet
        :return: Returns the node_id of the next hope node
        :rtype: int
        """
        next_hop = super().get_next_hop(packet)
        dest = str(packet.destination_id)
        try:
            next_hop = int(self.routes[dest])
        except KeyError:
            if packet.type == PacketType.CONTROL:
                return self.netstack.BROADCAST_ADDRESS
        return next_hop

    def get_net_neighbors(self) -> List[int]:
        """Retrieves all of the network layer neighbors according to the next hop table

        :return: A list of node_ids corresponding to the network layer neighbors of this node
        :rtype: List[int]
        """
        neighbors = []
        if self.routes is not None:
            for dest, next_hop in self.routes.items():
                if neighbors.count(int(next_hop)) > 0:
                    pass
                else:
                    neighbors.append(int(next_hop))
        return neighbors
