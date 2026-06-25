from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode

import numpy as np
import random
from lure.config.configuration import Config
from lure.node.stats import StatType
from lure.node.traffic.traffic_generator import TrafficGenerator
from lure.node.stats import Stats, StatsProvider

# Example of how to use this class in python:
# ***************************************************
#     generator = PoissonTrafficGenerator(parameters...)

#     t_step = 1 # the unit of execution in simulator, i.e. every 1 ms.

#     for t in range(0, t_max, t_step) # run the simulation (and therefore the traffic generator) for t_max time.
#         generator.run_timer(t_step)
#         ...
#         if generator.packet_is_generated():
#             ... # generate a packet here
#         else:
#             pass # no packet generated


# ***************************************************
class PoissonTrafficGenerator(TrafficGenerator):
    """A traffic generator designed to follow a Poisson process"""

    TIMER_KEY_GENERATE_PACKET = "traffic_generate"

    def __init__(self, config: Config):
        super().__init__(config)
        self.rate = None
        config.extract("rate", self, 0.001)
        # self.timer = 0
        # self.pkt_count = 0
        self.prev_generation_time = 0
        self.prev_generation_interval = None

    def initialize(self, node: "SensorNode"):
        """Initialize with the simulation

        :param node: The node this traffic generator is associated it
        :type node: SensorNode
        """
        self.stats.set(StatType.NODE_TRAFFIC_RATE, self.rate)
        self.timestepper = node.timestepper
        self.timestepper.set_relative_timer(
            self.TIMER_KEY_GENERATE_PACKET, self._time_to_next_send()
        )

    def _time_to_next_send(self):
        """The time until a next packet should arrive

        :return: The duration in ms that another packet should arrive in
        :rtype: _type_
        """
        U = random.uniform(0, 1)
        t = max(-np.log(U) / self.rate, 1)
        self.stats.list_append(StatType.PACKET_ARRIVAL_INTERVALS, t)
        return t

    def generate(self) -> int:
        """Generate packets based upon a Poisson process

        :return: The number of packets generated
        :rtype: int
        """
        elapsed = self.timestepper.simpy_env.now - self.prev_generation_time
        current_pkt_count = 0

        if self.prev_generation_interval:
            elapsed -= self.prev_generation_interval

        while elapsed > 0:
            current_pkt_count += 1
            elapsed -= self._time_to_next_send()

        self.prev_generation_interval = abs(elapsed)
        self.prev_generation_time = self.timestepper.simpy_env.now
        self.timestepper.set_relative_timer(
            self.TIMER_KEY_GENERATE_PACKET, self.prev_generation_interval
        )

        # curr_pkt_count = self.pkt_count
        # # reset pkt_count
        # self.reset_pkt_count()
        self.stats.update(StatType.PACKETS_GENERATED, current_pkt_count)
        return current_pkt_count

    def __str__(self):
        return f"Poisson-{self.rate}"

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.stats.register(StatType.NODE_TRAFFIC_RATE)
