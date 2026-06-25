from abc import ABC, abstractmethod
from random import Random
import simpy
from typing import TYPE_CHECKING, Dict, List

from lure.node.timestepper import Timestepper

if TYPE_CHECKING:
    from lure.simulation import Simulation
    from lure.node.power.harvester import Harvester
from lure.config.configuration import EnergyModelConfig
from lure.lure_logger import Loggable


class EnergyModelObserver(ABC):
    @abstractmethod
    def on_update(self):
        """Called when the energy model is updated, i.e. when available charging power changes."""
        pass


class EnergyModel(Loggable):
    """Models Energy available to the simulation"""

    def __init__(self, config: EnergyModelConfig):
        self.update_interval_ms = None
        config.extract("update_interval_ms", self, 10000)

        self.random: Random = Random()

        # Track a separate power for each Harvester
        self._current_powers: Dict["Harvester", float] = dict()
        self._last_sample_time = 0

        self._timesteppers: List[Timestepper] = []

        self._observers: List[EnergyModelObserver] = []

    def current_power_w(self, harvester: "Harvester") -> float:
        """Retrieves the current power for a given harvester in Watts

        :param harvester: The harvester being evaluated for current power
        :type harvester: Harvester
        :return: Power in watts
        :rtype: float
        """
        return self._current_powers[harvester]

    def initialize(self, sim: "Simulation"):
        """Initialize with the simulation

        :param sim: The simulation object this energy model is associated with
        :type sim: Simulation
        """
        self.random.seed(a=sim.seed)
        for n in sim.nodes:
            self._timesteppers.append(n.timestepper)

    def register_observer(self, observer: EnergyModelObserver):
        """Registers an observer for this energy model

        :param observer: The observer being registered to this object
        :type observer: EnergyModelObserver
        """
        self._observers.append(observer)

    def register_harvester(self, harvester: "Harvester"):
        """Registers a harvester (belonging to a particular node) to this energy model

        :param harvester: The harvester being registered
        :type harvester: Harvester
        """
        self._current_powers[harvester] = self._get_next_power(harvester)

    def _get_next_power(self, harvester: "Harvester") -> float:
        """Retrieves the next power for a given harvester

        :param harvester: Harvester being queried about
        :type harvester: Harvester
        :return: A float representing the next power for the harvester
        :rtype: float
        """
        return 0

    def get_avg_power(self) -> float:
        """Retrieves the average power in the distribution

        :return: Power in watts
        :rtype: float
        """
        return 0

    # SimPy process for the energy model.
    def execute(self, simpy_env: simpy.Environment):
        """The simpy process for the energy model. Used for time evlauations

        :param simpy_env: The SimPy environment associated with this energy model
        :type simpy_env: simpy.Environment
        """
        while True:
            for h in self._current_powers.keys():
                self._current_powers[h] = self._get_next_power(h)
            self.debug(f"New charging powers: {self._current_powers}")
            for o in self._observers:
                o.on_update()
            self._last_sample_time = simpy_env.now
            for t in self._timesteppers:
                t.set_relative_timer("em_update", self.update_interval_ms)
            yield simpy_env.timeout(self.update_interval_ms)

    def __str__(self):
        return "EnergyModel"
