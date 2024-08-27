from lure.config.configuration import Config
from lure.node.net.packet import Packet
from lure.node.stats import Stats, StatType, StatsProvider
from lure.node.time.time import TimeModule
from lure.node.time.persistent_clock import PersistentClock
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode

class ContinuousTimeModule(TimeModule):
    def __init__(self, config: Config):
        super().__init__(config)
        self.persistent_clock: PersistentClock = Config.instantiate_from_dict(config.config["persistent_clock"], 'lure.node.time')
        self.cont_local_time = 0
        self.is_dead_period = False
        self.last_pclk_est = 0
        self.max_meas_time = 0
        self.ref_node_id = None
        self.TS_KEY = "timestamp"
        self.is_root = False


    def initialize(self, node: 'SensorNode'):
        super().initialize(node)
        self.node_id = node.node_id

    def time(self) -> int:
        """
        The function returns the local time.
        :return: The method `time` is returning an integer value, specifically the value of
        `self.cont_local_time`.
        """
        return self.cont_local_time

    def boot(self, t: int):
        """
        The `boot` function estimates the off-time of a clock and updates the continuous local time and
        statistics.
        
        :param t: The parameter "t" in the "boot" method represents the current off-time. It is an integer value
        that indicates the current time in some unit of measurement (e.g., seconds, milliseconds, etc.)
        :type t: int
        """
        self._last_update = self.timestepper.simpy_env.now
        self.active_clock.reset()
        # Estimate off-time with persistent clock
        self.last_pclk_est, self.is_dead_period, self.max_meas_time = self.persistent_clock.get_est_offtimes(t)
        self.debug(f"Node: {self.node_id}, Est pclk time: {self.last_pclk_est}")
        if self.is_dead_period:
            self.stats.time_series_append(StatType.CLK_DEAD_PERIOD, None)
        # Append estimated off-time from pclk and continuous local time for stats
        self.stats.time_series_append(StatType.PCLK_EST_TIME, self.last_pclk_est)
        
    def execute(self):
        """
        The function updates the local time based on the difference between the current time and the last
        update time.
        """
        if self._last_update is not None:
            self.cont_local_time += self.active_clock.update(self.timestepper.simpy_env.now - self._last_update)
        self._last_update = self.timestepper.simpy_env.now

    def frame(self, packet: Packet) -> bool:
        """
        The frame function sets the header of a packet with a time stamp if the node id is 0, and returns
        True, otherwise it returns False.
        
        :param packet: The `packet` parameter is an instance of the `Packet` class. It represents the packet
        that is being processed by the `frame` method
        :type packet: Packet
        :return: a boolean value. If the node_id is 0, it sets the header of the packet with a time stamp
        and returns True. Otherwise, it returns False.
        """
        # packet sent only by root node with id 0
        if self.node_id == 0:
            packet.set_header(self.TS_KEY, self.cont_local_time, 4)
            self.debug(f"Sent Time Stamp {self.cont_local_time}")
            return True
        else: 
            return False

    def parse(self, packet: Packet) -> bool:
        """
        The parse function takes a packet as input and returns False. Called for every incoming packet. Use this to pop headers out of the packet.
        
        :param packet: The parameter "packet" is of type "Packet". It is likely an object that represents a
        network packet or a data packet
        :type packet: Packet
        :return: a boolean value of False.
        """
        return False

    # TODO: how to allow the time module to generate and send its own packets?
    # A temporary workaround would be to have SensorNode pass the Netstack object to the time module in sensor_node.init_with_simulation()

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.active_clock.stats = stats
        self.persistent_clock.stats = stats

        self.stats.register_time_series(StatType.PCLK_EST_TIME)
        self.stats.register_time_series(StatType.CONT_LCL_TIME)
        self.stats.register_time_series(StatType.EST_SHARED_TIME)
        self.stats.register_time_series(StatType.SUCC_COMM)
        self.stats.register_time_series(StatType.CLK_DEAD_PERIOD)
        self.stats.register_time_series(StatType.EST_SHARED_TIME_TM)
