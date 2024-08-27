# Base class for a traffic generator, which determines when the node generates packets
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode
from lure.config.configuration import Config
from lure.lure_logger import Loggable
from lure.node.stats import StatsProvider


class TrafficGenerator(Loggable, StatsProvider):
    """Controls packet generation for a node
    """

    def __init__(self, config: Config):
        pass

    def initialize(self, node: 'SensorNode'):
        """Initialize with the simulation

        :param node: The node this traffic generator is associated with
        :type node: SensorNode
        """
        pass

    def generate(self) -> int:
        """Called every simulated timestep that the node is operating

        :return: The number of packets generated
        :rtype: int
        """
        return 0

    def __str__(self):
        return 'TrafficGenerator'