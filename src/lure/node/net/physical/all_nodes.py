from typing import List

from lure.config.configuration import Config
from lure.node.net import Netstack
from lure.node.sensor_node import SensorNode
from lure.node.net.physical.physical import Physical


class AllNodesPhysical(Physical):
    """This class defines a complete mesh topology of all the nodes in the simulation"""

    def __init__(self, config: Config):
        super().__init__(config)
        self.num_nodes = None

    def initialize(self, node: SensorNode, all_netstacks: List["Netstack"]):
        """Initialize with the simulation. Establish the physical topology.

        :param node: The node this protocol belongs to
        :type node: SensorNode
        :param all_netstacks: All netstacks in the simulation
        :type all_netstacks: List[&#39;Netstack&#39;]
        """
        super().initialize(node, all_netstacks)
        num_nodes = 1 + len(all_netstacks)
        node_ids = range(num_nodes)
        self.neighbor_list = [n for n in node_ids if n != self.netstack.addr]
