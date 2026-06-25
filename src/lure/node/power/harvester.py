from typing import TYPE_CHECKING
from simpy.core import SimTime

if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode
from lure.config.configuration import Config
from lure.energy.energy_model import EnergyModel
from lure.lure_logger import Loggable

from lure.node.stats import StatType, StatsProvider, Stats


class Harvester(Loggable, StatsProvider):
    """The energy harvester for a node"""

    def __init__(self, config: Config):
        self.loss_factor = None
        config.extract("loss_factor", self, 0.01)
        self._charging_power = 0

    @property
    def charging_power(self) -> float:
        """Current charging power in Watts

        :return: Current charging power in Watts
        :rtype: float
        """
        return self._charging_power

    @charging_power.setter
    def charging_power(self, p: float):
        if p != self._charging_power:
            self.stats.time_series_append(StatType.HARVESTER_CHARGING_POWER, p)
            self._charging_power = p

    def initialize(self, node: "SensorNode", energy_model: EnergyModel):
        """Initialize the harvester. Called before the simulation starts

        :param node: The node this harvester belongs to
        :type node: SensorNode
        :param energy_model: The energy model for this simulation
        :type energy_model: EnergyModel
        """
        self.energy_model = energy_model
        self.energy_model.register_harvester(self)
        self.charging_power = self.get_next_charging_power()

    def restart(self):
        """Called when this node turns on"""
        pass

    def get_next_charging_power(self) -> float:
        """Retrieves the next charging power in watts

        :return: The next charging power in watts
        :rtype: float
        """
        return self.energy_model.current_power_w(self) * self.loss_factor

    def harvest(self, t: float) -> float:
        """Harvests energy for the last t ms. Called for each simulated timestep. Should not be overriden.

        :param t: Time in ms
        :type t: float
        :return: Energy harvest in the last t ms
        :rtype: float
        """
        # Use the "old" charging power to calculate harvested energy over the last t.
        # If the charging power changes, it will be because it JUST changed this timestamp.
        energy = self.charging_power * t
        self.charging_power = self.get_next_charging_power()
        return energy

    def get_time_to_harvest(self, energy: float) -> SimTime:
        """Returns the expected time required to harvest a given energy amount. Used for scheduling node events

        :param energy: The energy to be estimated for collection
        :type energy: float
        :return: The amount of time in ms that it will take to harvest energy
        :rtype: SimTime
        """
        if self.charging_power == 0:
            self.warning("Zero charging power at call to get_time_to_harvest().")
            return None
        return energy / self.charging_power

    def __str__(self):
        return f"Harvester-{self.loss_factor}"

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
