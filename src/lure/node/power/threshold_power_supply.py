from simpy.core import SimTime
from lure.config.configuration import Config
from lure.node.power.power_supply import PowerSupply


# A simple power supply that harvests as much energy as possible from the environment,
# given a nominal lifecycle ratio, and stores it in a Capacitor.
class ThresholdPowerSupply(PowerSupply):
    """A PowerSupply that turns on/off based on storage voltage thresholds"""

    def __init__(self, config: Config):
        self.threshold_to_die_v = None
        self.threshold_to_restart_v = None
        config.extract("threshold_to_die_v", self, 1.0)
        config.extract("threshold_to_restart_v", self, 1.23)
        super().__init__(config)

    def set_charge_percent(self, percent: float):
        current_energy = self.get_current_energy()
        energy_high = self.storage.get_energy_for_voltage(self.threshold_to_restart_v)
        energy_low = self.storage.get_energy_for_voltage(self.threshold_to_die_v)
        energy = percent / 100 * (energy_high - energy_low) + energy_low
        self.storage.change_energy(energy - current_energy)

    def execute(self, discharge_rate: float) -> bool:
        super().execute(discharge_rate)
        return self.storage.voltage > self.threshold_to_die_v

    def get_max_ontime_energy(self) -> float:
        return self.storage.get_energy_for_voltage(self.threshold_to_restart_v) - self.storage.get_energy_for_voltage(self.threshold_to_die_v)

    def get_time_to_restart(self) -> SimTime:
        remaining_energy = self.storage.get_energy_for_voltage(self.threshold_to_restart_v) - self.get_current_energy()
        if remaining_energy <= 0:
            return 0
        return self.harvester.get_time_to_harvest(remaining_energy)

    def get_time_to_death(self, discharge_rate: float) -> SimTime:
        remaining_energy = self.get_current_energy() - self.storage.get_energy_for_voltage(self.threshold_to_die_v)
        if remaining_energy <= 0:
            return 0
        return remaining_energy / discharge_rate

    def get_expected_period_for_rate(self, rate_w: float) -> SimTime:
        energy = self.storage.get_energy_for_voltage(self.threshold_to_restart_v) - self.storage.get_energy_for_voltage(self.threshold_to_die_v)
        return energy / rate_w

    def __str__(self):
        return f'ThresholdPowerSupply-{super().__str__()}'
