import math
from lure.config.configuration import Config
from lure.lure_logger import Loggable
from lure.node.stats import StatType, StatsProvider


class Storage(Loggable, StatsProvider):
    """An energy storage object for a node."""

    def __init__(self, config: Config):
        """Instantiates a Storage

        :param config: the configuration to use
        :type config: Config
        """
        self._voltage = 0  # V

    @property
    def voltage(self) -> float:
        """The voltage across this Storage."""
        return self._voltage

    @voltage.setter
    def voltage(self, v: float):
        self.stats.time_series_append(StatType.STORAGE_VOLTAGE, v)
        self._voltage = v

    def get_energy_for_voltage(self, voltage: float) -> float:
        """Returns the amount of energy stored for a given voltage.

        :param voltage: the voltage, in Volts
        :type voltage: float
        :return: energy in mJ
        :rtype: float
        """
        pass

    def get_energy(self) -> float:
        """Returns the current energy stored

        :return: current energy, in mJ
        :rtype: float
        """
        pass

    def change_energy(self, amount: float) -> bool:
        """Modifies the energy in the Storage

        :param amount: the requested change to the energy, in mJ. Can be positive or negative.
        :type amount: float
        :return: True if the storage device can support the energy change, False if not (e.g. due to lack of energy)
        :rtype: bool
        """
        pass

    def __str__(self):
        return "Storage"


class Capacitor(Storage):
    """A model of a capacitor energy storage device."""

    def __init__(self, config: Config):
        super().__init__(config)
        self.capacitance_mf = None  # mF
        self.max_voltage = None  # V
        config.extract("capacitance_mf", self, 50.0)
        config.extract("max_voltage", self, 2.0)

    def get_energy_for_voltage(self, voltage: float) -> float:
        return self.capacitance_mf * voltage * voltage / 2.0

    def get_energy(self) -> float:
        return self.get_energy_for_voltage(self.voltage)

    def change_energy(self, amount: float) -> bool:
        """Modifies the energy in the Capacitor.

        :param amount: the requested change to the energy, in mJ. Can be positive or negative. Energy that would push the Capacitor over its maximum voltage is ignored.
        :type amount: float
        :return: True if the Capacitor has enough energy to support the change, False if not
        :rtype: bool
        """
        energy = max(self.get_energy() + amount, 0)
        v = self._get_voltage_for_energy(energy)

        if v > self.max_voltage:
            self.voltage = self.max_voltage
            self.debug("Overvoltage on capacitor, excess energy dumped")
            return True
        elif v < 0:
            self.voltage = 0
            self.debug("Negative voltage on capacitor, ignored")
            return False

        self.voltage = v
        return True

    def _get_voltage_for_energy(self, energy: float) -> float:
        return math.sqrt(2.0 * energy / self.capacitance_mf)

    def __str__(self):
        return f"Capacitor-{self.capacitance_mf}"
