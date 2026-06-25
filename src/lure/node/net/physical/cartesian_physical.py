from typing import Tuple, List
import math

from lure.node.stats import Stats, StatType, StatsProvider
from lure.config.configuration import Config
from lure.node.net import Netstack
from lure.node.sensor_node import SensorNode
from lure.node.net.physical.physical import Physical

RANGE_LIMIT = 4


class CartesianPhysical(Physical):
    """A class that establishes the physical topology based upon a cartesian coordinate system"""

    def __init__(self, config: Config):
        super().__init__(config)
        self.position_x = None
        self.position_y = None
        config.extract("position_x", self, None)  # Eventually will be a config
        config.extract("position_y", self, None)  # Eventually will be a config
        self.position: Tuple(int, int) = (self.position_x, self.position_y)

    def initialize(self, node: SensorNode, all_netstacks: List["Netstack"]):
        """Initialize with the simulation. Establishes this node's physical neighbors

        :param node: _description_
        :type node: SensorNode
        :param all_netstacks: _description_
        :type all_netstacks: List[&#39;Netstack&#39;]
        """
        super().initialize(node, all_netstacks)
        self.neighbor_list = self.get_neighbors()
        self.stats.list_append(StatType.PHYSICAL_NEIGHBORS, self.neighbor_list)

    def get_distance(self, receiver_node: "Netstack"):
        """Retrieves the distance between this node and another node in cartesian coordinate units via the pythagorean theorem

        :param receiver_node: The node being compared to
        :type receiver_node: Netstack
        :return: The distance in cartesian coordinate units units
        :rtype: _type_
        """
        distance_x = self.position[0] - receiver_node.physical.position[0]
        distance_y = self.position[1] - receiver_node.physical.position[1]
        distance = math.sqrt((distance_x**2) + (distance_y**2))
        return distance

    def get_neighbors(self) -> List[int]:
        """Determines physical neighbors by comparing measurements from :py:meth:`lure.node.net.physical.cartesian_physical.CartesianPhysical.get_distance` \
        with the RANGE_LIMIT constant set in this module

        :return: All neighbor IDs of this node
        :rtype: List[int]
        """
        neighbors = []
        for node in self.all_netstacks:
            if self.get_distance(node) <= RANGE_LIMIT:
                neighbors.append(int(node.addr))
        return neighbors

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.stats.register_list(StatType.PHYSICAL_NEIGHBORS)
