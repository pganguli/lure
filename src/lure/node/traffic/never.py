# Sends no traffic. Useful for a receiver-only node.
from lure.node.traffic.traffic_generator import TrafficGenerator

class NeverTrafficGenerator(TrafficGenerator):
    """A traffic generator that never generates packets
    """

    def __str__(str):
        return 'Never'

