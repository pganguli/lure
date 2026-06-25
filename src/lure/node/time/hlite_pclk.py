from lure.config.configuration import Config
from lure.node.time.persistent_clock import PersistentClock

import numpy as np


class HarcLitePersistentClock(PersistentClock):
    def __init__(self, config: Config):
        super().__init__(config)

    def get_est_offtimes(self, input_off_time):
        """
        The function `get_est_offtimes` takes an input off time, converts it to the appropriate units,
        calculates estimated off times and other measurements, and returns the results.

        :param input_off_time: The input_off_time is a single value representing the off time in
        milliseconds
        :return: three values:
        1. The estimated off time (converted to an integer)
        2. The maximum measurement list (flattened)
        3. The maximum measurement time for harc-lite clock type
        """
        input_off_times = []
        if self.time_units == "ms":
            input_off_times.append(np.divide(input_off_time, 1000))
        # Get voltage from the off time for test data
        (
            comp_clk_est_time,
            est_off_times,
            maxMeasurementAllChannels,
            max_meas_list,
            max_meas_time_hlite,
        ) = self.cal_est_time_from_offtime(input_off_times, clk_type="harc-lite")
        max_meas_list = np.asarray(max_meas_list, dtype=object)
        if self.time_units == "ms":
            est_off_times = np.multiply(est_off_times, 1000)
        return int(est_off_times[0]), max_meas_list.flatten()[0], max_meas_time_hlite
