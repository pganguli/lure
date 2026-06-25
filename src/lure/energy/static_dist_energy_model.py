from enum import Enum

from lure.energy.energy_model import EnergyModel, EnergyModelConfig
from lure.node.power.harvester import Harvester


class DistType(Enum):
    """Different distribution types available to this energy model"""

    GAUSSIAN = "GAUSSIAN"  # Params [mean, std]
    GAUSSIAN_COEFFICIENT = (
        "GAUSSIAN_COEFFICIENT"  # Params [mean, coeff], where std = mean * coeff
    )


class StaticDistEnergyModel(EnergyModel):
    """An energy model that uses a static distribution"""

    def __init__(self, config: EnergyModelConfig):
        self.dist_type = None
        self.param1 = None
        self.param2 = None
        config.extract("dist_type", self, "GAUSSIAN")
        config.extract("param1", self, 0.06)
        config.extract("param2", self, 0.018)

        self.dist_type = DistType(self.dist_type)

        super().__init__(config)

    def _get_next_power(self, harvester: Harvester) -> float:
        """Uses the distribution to generate the next power for a given harvester

        :param harvester: The harvester being evaluated
        :type harvester: Harvester
        :return: The power in watts
        :rtype: float
        """
        if self.dist_type is DistType.GAUSSIAN:
            power = self.random.gauss(self.param1, self.param2)
        elif self.dist_type is DistType.GAUSSIAN_COEFFICIENT:
            if self.param2 == 0:
                power = self.param1
            else:
                power = self.random.gauss(self.param1, self.param1 * self.param2)
        else:
            power = 0

        return max(power, 0)

    def get_avg_power(self) -> float:
        """Average power for the distribution

        :return: The average power in watts
        :rtype: float
        """
        if (
            self.dist_type is DistType.GAUSSIAN
            or self.dist_type is DistType.GAUSSIAN_COEFFICIENT
        ):
            return self.param1
        else:
            self.warning(f"No average power defined for distribution {self.dist_type}")
        return self.param1

    def __str__(self):
        return f"StaticDist-{self.dist_type.value}-{self.param1}-{self.param2}"
