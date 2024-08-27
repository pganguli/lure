import random
from typing import TYPE_CHECKING

from simpy.core import SimTime

if TYPE_CHECKING:
    from lure.energy.energy_model import EnergyModel
    from lure.node.sensor_node import SensorNode

from lure.config.configuration import Config
from lure.lure_logger import Loggable

from lure.node.power.harvester import Harvester
from lure.node.power.storage import Storage
from lure.node.stats import Stats, StatsProvider

INITIAL_CHARGE_RANDOM_UNIFORM = 'random_uniform'

class PowerSupply(Loggable, StatsProvider):
    """The power module for a node, which ties the storage and the harvester together."""

    def __init__(self, config: Config):
        """Instantiate the PowerSupply
        
        :param config: the configuration
        :type config: Config
        """
        self.storage: Storage = Config.instantiate_from_dict(config.config["storage"], 'lure.node.power')
        self.harvester: Harvester = Config.instantiate_from_dict(config.config["harvester"], 'lure.node.power')
        self.initial_charge_percent = None
        self._last_update = 0
        self._last_discharge_rate = 0
        self.timestepper = None
        config.extract("initial_charge_percent", self, 100)

    def initialize(self, node: 'SensorNode', energy_model: 'EnergyModel'):
        """Initialize the PowerSupply, called during the deployment phase (i.e. the beginning of the simulation).

        :param node: the SensorNode this is powering
        :type node: SensorNode
        :param energy_model: the EnergyModel for the simulation, used to register the Harvester
        :type energy_model: EnergyModel
        """
        self.harvester.initialize(node, energy_model)
        self.timestepper = node.timestepper
        if self.initial_charge_percent == INITIAL_CHARGE_RANDOM_UNIFORM:
            percent = random.random() * 100
        else:
            percent = self.initial_charge_percent
        self.set_charge_percent(percent)

    def set_charge_percent(self, percent: float):
        """Sets the storage to the given percent charge
        
        :param percent: the percentage of charge the storage will now have
        :type percent: float
        """
        pass
    
    def restart(self):
        """Maintenance actions for when the node restarts."""
        self.harvester.restart()

    def execute(self, discharge_rate: float) -> bool:
        """Called every time the node executes. Used to harvest and discharge based on time passed.
        
        :param discharge_rate: the discharge rate in Watts since the last time execute was called
        :type discharge_rate: float
        :return: True if the PowerSupply has enough energy to support the requested discharge, False if not (and the node should turn off)
        :rtype: bool
        """
        elapsed_time = self.timestepper.simpy_env.now - self._last_update
        self.storage.change_energy(self.harvester.harvest(elapsed_time) - discharge_rate*elapsed_time)
        self._last_discharge_rate = discharge_rate
        self._last_update = self.timestepper.simpy_env.now
        return self.storage.voltage > 0

    def get_current_energy(self) -> float:
        """Gets the current energy of the storage, calling execute() if needed.
        
        :return: the current stored energy, in mJ
        :rtype: float
        """
        if self.timestepper.simpy_env.now > self._last_update:
            self.execute(self._last_discharge_rate)
        return self.storage.get_energy()

    def get_time_to_restart(self) -> SimTime:
        """Gets expected time in ms until the PowerSupply has enough energy to restart. Used for scheduling node events
        
        :return: time until the node can restart
        :rtype: SimTime
        """
        pass

    def get_time_to_death(self, discharge_rate: float) -> SimTime:
        """Gets expected time in ms until the PowerSupply will turn off due to low voltage. Used for scheduling node events
        
        :param discharge_rate: the current discharge rate, in Watts
        :type discharge_rate: float
        :return: time until the node will turn off
        :rtype: SimTime
        """
        pass

    def get_max_ontime_energy(self) -> float:
        """Returns the maximum amount of energy that can be stored at the start of an on-time
        
        :return: max energy at start of an on-time, in mJ
        :rtype: float
        """
        pass

    def get_expected_period_for_rate(self, rate_w: float) -> SimTime:
        """Returns the estimated length of a lifecycle given a
        charging rate and assuming a full on-time.
        
        :param rate_w: the charging rate to compute the estimate for, in Watts
        :type rate_w: float
        :return: length of the lifecycle for that rate
        :rtype: SimTime
        """
        pass

    def __str__(self):
        return f'{self.storage}_{self.harvester}'

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.storage.stats = stats
        self.harvester.stats = stats