# LMP based on the stateless LMP framework (MASS 2021), where the node is on for a fixed amount of time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode

from lure.node.node_state import NodeState

from lure.config.configuration import Config
from lure.node.lmp.lmp import *
from lure.node.time.time import TimeModule
from lure.node.stats import StatType


class FixedLMP(LMP):
    """A LMP with a fixed on-time"""

    TIMER_KEY_ON_TIME = "lmp_on_time"

    def __init__(self, config: Config):
        super().__init__(config)
        self._on_time_ms = None
        self.initial_on_time_ms = config.config["on_time_ms"]
        # config.extract("on_time_ms", self, 10)
        self.time_module: TimeModule = None

    @property
    def on_time_ms(self):
        """A property defining how much on time should pass before the LMP early-dies

        :return: The current on-time duration (ms)
        :rtype: int
        """
        return self._on_time_ms

    @on_time_ms.setter
    def on_time_ms(self, t: int):
        if t != self._on_time_ms:
            self._on_time_ms = t
            self.stats.time_series_append(StatType.LMP_ON_TIME, t)

    def initialize(self, node: "SensorNode"):
        """Initialize with the simulation

        :param node: The node that this LMP belongs to
        :type node: SensorNode
        """
        super().initialize(node)
        self.on_time_ms = self.initial_on_time_ms
        self.time_module = node.time_module

    def set_config(self, key: LMPConfigKey, value) -> bool:
        """Set a configuration value identified by key

        :param key: The key identifying a configuration type
        :type key: LMPConfigKey
        :param value: The value to set the configuration to
        :type value: any
        :return: True if the LMP in not locked and on_time_ms is being set
        :rtype: bool
        """
        if key is LMPConfigKey.ON_TIME_MS:
            if self.locked:
                return False
            try:
                self.on_time_ms = value + 0
                if self.on_time_ms > 0:
                    self.time_module.set_absolute_timer(
                        self.TIMER_KEY_ON_TIME, self.on_time_ms
                    )
                return True
            except ValueError:
                self.debug(f"Error: {value} not valid for {key} in LMP")
                return False
        else:
            return super().set_config(key, value)

    def get_config(self, key: LMPConfigKey) -> Any:
        """Get a configuration value identified by key

        :param key: The key identifying the configuration
        :type key: LMPConfigKey
        :return: The value of the configuration
        :rtype: Any
        """
        if key is LMPConfigKey.ON_TIME_MS:
            return self.on_time_ms
        else:
            self.debug(f"Error: {key} not found in LMP")
        return None

    def boot(self):
        """Executed on node boot"""
        super().boot()
        self.set_config(LMPConfigKey.ON_TIME_MS, self.initial_on_time_ms)

    def enable(self, lock: bool = False):
        """Enables the lmp

        :param lock: If True the LMP becomes locked, defaults to False
        :type lock: bool, optional
        """
        # if not self.enabled or (lock and not self.locked):
        super().enable(lock)
        # if self.get_config(LMPConfigKey.ON_TIME_MS) - self.time_module.clock() < self.initial_on_time_ms:
        #    self.set_config(LMPConfigKey.ON_TIME_MS, self.time_module.clock() + self.initial_on_time_ms)
        if self.enabled and self.on_time_ms >= self.time_module.clock():
            self.time_module.set_absolute_timer(self.TIMER_KEY_ON_TIME, self.on_time_ms)

    def disable(self):
        """Disables the lmp"""
        super().disable()
        if not self.enabled:
            self.time_module.cancel_timer(self.TIMER_KEY_ON_TIME)

    def execute(self) -> NodeState:
        """Called every exectution cycle (1 ms)

        :return: True if the noded should (immediately) early-die, else False
        :rtype: NodeState
        """
        self.debug(
            f"is enabled: {self.enabled}, lmp: {self.on_time_ms}, time since boot: {self.time_module.clock()}"
        )
        ret = (
            self.enabled
            and self.on_time_ms > 0
            and self.time_module.clock() >= self.on_time_ms - 0.000001
        )
        if ret:
            self.stats.time_series_append(
                StatType.LMP_EARLY_DIE, self.time_module.clock()
            )
            return NodeState.OFF

        # self.time_module.set_absolute_timer(self.TIMER_KEY_ON_TIME, self.on_time_ms)
        return NodeState.OPERATING

    def __str__(self):
        return f"FixedLMP-{self.on_time_ms}"
