from simpy.core import SimTime
from typing import TYPE_CHECKING, Dict, Union
if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode

from lure.node.stats import Stats, StatsProvider
from lure.lure_logger import Loggable
from lure.config.configuration import Config
from lure.node.net.packet import Framer, Packet
from simpy.core import SimTime

NodeTime = Union[int, float]

class TimeModule(Framer, Loggable, StatsProvider):

    def __init__(self, config: Config):
        self.active_clock = Config.instantiate_from_dict(config.config["active_clock"], 'lure.node.time')
        self._timers: Dict[str, NodeTime] = dict()
        self._last_update: SimTime = None
        self.total_ontime: NodeTime = 0
        self._last_total_ontime_update: NodeTime = 0
        self.last_ontime = 0

    def initialize(self, node: 'SensorNode'):
        self.timestepper = node.timestepper
        self.netstack = node.netstack

    # Returns best guess of reference time, i.e. continuous/shared sense of time
    def time(self) -> int:
        if self.clock() > self._last_total_ontime_update:
            self.total_ontime += self.clock() - self._last_total_ontime_update
            self._last_total_ontime_update = self.clock()
        return self.total_ontime

    # Returns best guess of time since boot
    def clock(self) -> int:
        if self._last_update is not None:
            if self.timestepper.simpy_env.now - self._last_update > 0:
                self.execute()
        return self.active_clock.clock()

    # Called on node boot. t is the ground truth time that the node was off.
    def boot(self, t: int):
        self._last_update = self.timestepper.simpy_env.now
        self.active_clock.reset()
        self._last_total_ontime_update = self.clock()

    # Called right before the node dies
    def off(self):
        self.last_ontime = self.clock()

    # Called every simulated timestep that the node is on
    def execute(self):
        if self._last_update is not None:
            self.active_clock.update(self.timestepper.simpy_env.now - self._last_update)
        self._last_update = self.timestepper.simpy_env.now
        self.debug(f'Clock is now {self.clock()}')

    def set_relative_timer(self, key: str, t: NodeTime):
        self.debug(f'Setting {key} with {t}')
        self._timers[key] = self.clock() + t
        self.timestepper.set_relative_timer(key, self.node_time_to_sim_time(t))
        
    def set_absolute_timer(self, key: str, t: NodeTime):
        self.debug(f'Setting {key} to {t}')
        self._timers[key] = t
        self.timestepper.set_relative_timer(key, self.node_time_to_sim_time(t - self.clock()))

    def timer_expired(self, key: str) -> bool:
        try:
            self.debug(f'Checking if timer {key} for {self._timers[key]} is expired at {self.clock()}...')
            return self.clock() >= self._timers[key]
        except KeyError:
            self.warning(f'Timer {key} not found.')
            return False

    def cancel_timer(self, key: str):
        self._timers[key] = 0
        self.timestepper.cancel_timer(str)

    # TODO: support drift etc.
    def node_time_to_sim_time(self, t: NodeTime):
        return t

    # Called for every outgoing packet. Use this to add headers, e.g. time info, to the packet.
    def frame(self, packet: Packet) -> bool:
        return False

    # Called for every incoming packet. Use this to pop headers out of the packet.
    def parse(self, packet: Packet) -> bool:
        return False

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.active_clock.stats = stats
