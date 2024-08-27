import math
from simpy.core import SimTime
from typing import TYPE_CHECKING, Any
from lure.node.power.power_supply import PowerSupply

from lure.node.time.time import TimeModule
if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode

from lure.node.node_state import NodeState

from lure.config.configuration import Config
from lure.node.lmp.lmp import LMP, LMPConfigKey


class SoftIntermittencyLMP(LMP):
    """A basic LMP implementation of soft intermittency that requests a sleep state if voltage drops
    below a threshold and wakes if voltage rises above a threshold."""

    def __init__(self, config: Config):
        super().__init__(config)
        self.sleep_threshold_v = None
        self.wake_threshold_v = None
        config.extract("sleep_threshold_v", self, 2.0)
        config.extract("wake_threshold_v", self, 3.3)
        self.power_supply: PowerSupply = None
        self.sleeping_discharge_rate_w = None
        self.sleeping = False

    def initialize(self, node: 'SensorNode'):
        super().initialize(node)
        self.power_supply = node.power_supply
        self.sleeping_discharge_rate_w = node.discharge_rates[NodeState.SLEEPING]
        self.operating_discharge_rate_w = node.discharge_rates[NodeState.OPERATING]

    # Set a configuration value identified by key
    def set_config(self, key: LMPConfigKey, value) -> bool:
        if key is LMPConfigKey.SLEEP_THRESHOLD:
            try:
                self.sleep_threshold_v = float(value)
                return True
            except ValueError as e:
                self.debug(f'Error: {value} not valid for {key} in LMP')
                return False
        elif key is LMPConfigKey.WAKE_THRESHOLD:
            try:
                self.wake_threshold_v = float(value)
                return True
            except ValueError as e:
                self.debug(f'Error: {value} not valid for {key} in LMP')
                return False        
        else:
            return super().set_config(key, value)

    # Get a configuration value identified by key
    def get_config(self, key: LMPConfigKey) -> Any:
        if key is LMPConfigKey.SLEEP_THRESHOLD:
            return self.sleep_threshold_v
        elif key is LMPConfigKey.WAKE_THRESHOLD:
            return self.wake_threshold_v
        else:
            self.debug(f'Error: {key} not found in LMP')
        return None

    def boot(self):
        super().boot()
        self.sleeping = False

    # Called every execution cycle, i.e. every ms
    def execute(self) -> NodeState:  
        if self.power_supply.storage.voltage <= self.sleep_threshold_v:
            self.sleeping = True
            return NodeState.SLEEPING
        elif self.sleeping and self.power_supply.storage.voltage >= self.wake_threshold_v:
            self.sleeping = False
            return NodeState.OPERATING
        elif self.sleeping:
            return NodeState.SLEEPING
        
        return NodeState.OPERATING

    def get_time_til_wake(self) -> SimTime:
        if not self.sleeping:
            return None

        rate = self.power_supply.harvester.charging_power - self.sleeping_discharge_rate_w
        if rate == 0:
            return None

        return (self.power_supply.storage.get_energy_for_voltage(self.wake_threshold_v) - self.power_supply.get_current_energy()) / rate

    def get_time_til_sleep(self) -> SimTime:
        if self.sleeping:
            return None

        rate = self.operating_discharge_rate_w - self.power_supply.harvester.charging_power
        return (self.power_supply.get_current_energy() - self.power_supply.storage.get_energy_for_voltage(self.sleep_threshold_v)) / rate

    def __str__(self):
        return f'SoftIntermittencyLMP'

class SIClockLMP(SoftIntermittencyLMP):
    """A soft intermittency LMP that adds a clock element. The LMP will not wake the node from sleep until the max of either
    the voltage going over the wake threshold, or a timer timing out."""

    TIMER_KEY_WAKE = 'lmp_wake'

    def __init__(self, config: Config):
        super().__init__(config)
        self.time_module: TimeModule = None
        self.wake_time: int = None

    def initialize(self, node: 'SensorNode'):
        super().initialize(node)
        self.time_module = node.time_module

        # Set a configuration value identified by key
    def set_config(self, key: LMPConfigKey, value) -> bool:
        if key is LMPConfigKey.OTHER:
            if value is None:
                self.wake_time = None
                return True
            try:
                self.wake_time = float(value)
                self.time_module.set_relative_timer(self.TIMER_KEY_WAKE, self.wake_time - self.time_module.clock())
                return True
            except ValueError as e:
                self.debug(f'Error: {value} not valid for {key} in LMP')
                return False
        else:
            return super().set_config(key, value)

    # Get a configuration value identified by key
    def get_config(self, key: LMPConfigKey) -> Any:
        if key is LMPConfigKey.OTHER:
            return self.wake_time
        else:
            return super().get_config(key)

    def boot(self):
        super().boot()
        self.wake_time = None

    # Called every execution cycle, i.e. every ms
    def execute(self) -> NodeState:
        self.debug(f'wake_time {self.wake_time}, Timer expired {self.time_module.timer_expired(self.TIMER_KEY_WAKE)}, voltage {self.power_supply.storage.voltage}, wake_threshold {self.wake_threshold_v}')
        if self.power_supply.storage.voltage <= self.sleep_threshold_v:
            self.sleeping = True
        elif (self.sleeping) and self.power_supply.storage.voltage >= self.wake_threshold_v and (self.wake_time is None or self.time_module.timer_expired(self.TIMER_KEY_WAKE)):
            self.sleeping = False
            self.wake_time = None

        if self.sleeping:
            return NodeState.SLEEPING
        
        return NodeState.OPERATING

    def __str__(self):
        return f'SIClockLMP'