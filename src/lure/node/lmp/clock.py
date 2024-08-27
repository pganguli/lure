from typing import TYPE_CHECKING, Any
from lure.node.lmp.lmp import LMPConfigKey
if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode

from lure.node.node_state import NodeState

from lure.config.configuration import Config
from lure.node.lmp.fixed import FixedLMP
from lure.node.time.time import NodeTime, TimeModule
from lure.node.stats import StatType



class OracleEarlyDieClockLMP(FixedLMP):

    def __init__(self, config: Config):
        super().__init__(config)
        self.rendezvous_time = None
        self.max_on_time: NodeTime = None
        self.boot_time = None
        self.power_supply = None
        self._node = None

    def initialize(self, node: 'SensorNode'):
        super().initialize(node)
        self.max_on_time = node.power_supply.get_max_ontime_energy() / node.discharge_rates[NodeState.OPERATING] - node.os_boot_time_ms
        self.boot_time = node.os_boot_time_ms
        self.power_supply = node.power_supply
        self.discharge_rates = node.discharge_rates
        self._node = node

    # Set a configuration value identified by key
    def set_config(self, key: LMPConfigKey, value) -> bool:
        if key is LMPConfigKey.OTHER:
            if value is None:
                self.rendezvous_time = None
                return True
            try:
                self.rendezvous_time = float(value)
                if self._node.state is NodeState.OPERATING:
                    self._early_die_for_rendezvous()
                return True
            except ValueError as e:
                self.debug(f'Error: {value} not valid for {key} in LMP')
                return False
        else:
            return super().set_config(key, value)

    # Get a configuration value identified by key
    def get_config(self, key: LMPConfigKey) -> Any:
        if key is LMPConfigKey.OTHER:
            return self.rendezvous_time
        else:
            return super().get_config(key)

    def _early_die_for_rendezvous(self):
        curr_time = self.time_module.time()

        # If we can reach rendezvous this on time, we should stay on
        if curr_time + (self.max_on_time - self.time_module.clock()) >= self.rendezvous_time:
            self.set_config(LMPConfigKey.ON_TIME_MS, 0)
            self.rendezvous_time = None
            self.debug('Staying on for rendezvous!')

        else:
            max_offtime = self.power_supply.harvester.get_time_to_harvest(self.power_supply.get_max_ontime_energy())
            min_offtime = self.power_supply.get_time_to_restart()
            if max_offtime is None:
                max_offtime = 0
            if min_offtime is None:
                min_offtime = 0

            # If it's impossible for us to be on at the rendezvous, we should die now and hope
            if curr_time + min_offtime + self.boot_time >= self.rendezvous_time:
                self.debug(f'Cannot make rendezvous {self.rendezvous_time}... min offtime {min_offtime}')
                self.set_config(LMPConfigKey.ON_TIME_MS, self.time_module.clock())

            else:
                ttr_from_boot = self.rendezvous_time - (curr_time - self.time_module.clock())
                num_lifecycles = ttr_from_boot // (max_offtime + self.boot_time) + 1
                lifecycle_period = ttr_from_boot / num_lifecycles
                Pc = self.power_supply.harvester.get_next_charging_power()
                Ton = (lifecycle_period * Pc - self.boot_time * self.discharge_rates[NodeState.BOOTING]) / self.discharge_rates[NodeState.OPERATING]
                self.debug(f'Setting early die at {Ton} for rendezvous at {self.rendezvous_time} (planning on {num_lifecycles} lifecycles of {lifecycle_period})')
                if Ton >= self.time_module.clock():
                    self.set_config(LMPConfigKey.ON_TIME_MS, Ton)
                    #self.debug(f'Setting early die at {Ton} for rendezvous at {self.rendezvous_time} (planning on {num_lifecycles} lifecycles of {lifecycle_period})')
                else:
                    self.debug(f'Ton already passed... {Ton} vs. {self.time_module.clock()}')
                    #self.enable(lock=True)
                    self.set_config(LMPConfigKey.ON_TIME_MS, self.time_module.clock())

    def boot(self):
        super().boot()
        if self.rendezvous_time:
            self._early_die_for_rendezvous()

    def __str__(self):
        return f'OracleEarlyDieClockLMP'
