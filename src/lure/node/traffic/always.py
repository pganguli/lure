# Constantly sends traffic. Useful for a sender-only node.
from lure.node.stats import StatType
from lure.node.traffic.traffic_generator import TrafficGenerator

class AlwaysTrafficGenerator(TrafficGenerator):
    """A traffic generator that always generates 1 packet on a call of generate
    """

    def generate(self) -> int:
        """Returns the number of generated packets. In this case, 1.

        :return: A single packet
        :rtype: int
        """
        self.stats.increment(StatType.PACKETS_GENERATED)
        return 1

    def __str__(self):
        return 'Always'
        