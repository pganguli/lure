from typing import List

from lure.node.stats import Stats, StatType, StatsProvider
from lure.config.configuration import Config
from lure.node.net import Netstack
from lure.node.sensor_node import SensorNode
from lure.node.net.physical.physical import Physical


class ManualPhysical(Physical):
    def __init__(self, config: Config):
        super().__init__(config)
        self.neighbor_ids = None
        config.extract("neighbor_ids", self, None)

    def initialize(self, node: SensorNode, all_netstacks: List["Netstack"]):
        """The config setup for this is a bit odd, but this is a basic implementation anyways. \
        To declare whether a node in a system is a neighbor, submit a comma delineated list to "neighbor_ids" in your configuration. \
        For example, "neighbor_ids" : "2,3" declares that nodes 2 and 3 will be physical neighbors in this system
        """
        super().initialize(node, all_netstacks)
        # for node_id, bool in self.neighbor_ids.items():
        #     if int(bool) == 1:
        #         self.neighbor_list.append(int(node_id))
        self.neighbor_list = self.get_neighbors()
        self.critical(f"Neighbors = {self.neighbor_list}")
        for n in self.neighbor_list:
            self.stats.list_append(StatType.PHYSICAL_NEIGHBORS, n)

    def get_neighbors(self) -> List[int]:
        """Determines physical neighbors by comparing measurements from :py:meth:`lure.node.net.physical.cartesian_physical.CartesianPhysical.get_distance` \
        with the RANGE_LIMIT constant set in this module

        :return: All neighbor IDs of this node
        :rtype: List[int]
        """
        neighbors = self.neighbor_ids.split(",")
        for i in range(len(neighbors)):
            neighbors[i] = int(neighbors[i])
        return neighbors

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.stats.register_list(StatType.PHYSICAL_NEIGHBORS)
