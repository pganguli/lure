from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode
from lure.config.configuration import Config
from lure.node.power.harvester import Harvester
from lure.energy.energy_model import EnergyModel
from lure.node.stats import StatType, Stats, StatsProvider


class LifecycleRatioHarvester(Harvester):
    """Harvests energy based upon a lifecycle ratio (on-time/off-time)"""

    def __init__(self, config: Config):
        self.lifecycle_ratio = None
        config.extract("lifecycle_ratio", self, 0.01)
        super().__init__(config)

    # Initialize the harvester. Called before the simulation starts.
    def initialize(self, node: "SensorNode", energy_model: EnergyModel):
        """Initializes the harvester. Called before the simulation starts

        :param node: The node that this harvester belongs to
        :type node: SensorNode
        :param energy_model: The energy model for the simulation
        :type energy_model: EnergyModel
        """
        self.loss_factor = (
            self.lifecycle_ratio
            * node.get_avg_discharge_power_w()
            / energy_model.get_avg_power()
        )
        self.stats.set(StatType.NODE_LIFECYCLE_RATIO_NOMINAL, self.lifecycle_ratio)
        super().initialize(node, energy_model)

    def __str__(self):
        return f"LifecycleRatioHarvester-{self.lifecycle_ratio}"

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.stats.register(StatType.NODE_LIFECYCLE_RATIO_NOMINAL)
