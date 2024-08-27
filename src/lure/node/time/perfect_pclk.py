from lure.config.configuration import Config
from lure.node.time.persistent_clock import PersistentClock

import numpy as np

class PerfectPersistentClock(PersistentClock):
    def __init__(self, config: Config):
        super().__init__(config)
        self.max_meas_time = 50

    def est_time_perfect_clk(self, input_off_times):
        """
        The function `est_time_perfect_clk` takes a list of input off times and returns estimated off times
        and clock dead periods.
        
        :param input_off_times: A list of integers representing the times at which the clock is turned off
        :return: two lists: est_off_times and clock_dead_periods.
        """
        clock_dead_periods = []
        est_off_times = []
        for offtime in input_off_times:
            if offtime <= self.max_meas_time:
                est_off_times.append(input_off_times)
                clock_dead_periods.append(False)
            else:
                est_off_times.append(self.max_meas_time)
                clock_dead_periods.append(True)

        return est_off_times, clock_dead_periods

    def get_est_offtimes(self, input_off_time):
        """
        The function `get_est_offtimes` converts input off times from milliseconds to seconds if necessary,
        estimates the off times and clock dead periods, and returns the estimated off times in milliseconds,
        the clock dead periods, and the maximum measurement time in milliseconds.
        
        :param input_off_time: The `input_off_time` parameter is a single value representing the off time
        for a specific event
        :return: three values: 
        1. The estimated off time (est_off_times[0]) as an integer.
        2. The clock dead periods as a numpy array (clock_dead_periods) as an object.
        3. The maximum measurement time (self.max_meas_time*1000) multiplied by 1000.
        """
        input_off_times = []
        if self.time_units == "ms":
            input_off_times.append(np.divide(input_off_time, 1000))
        # Get voltage from the off time for test data
        est_off_times, clock_dead_periods =  self.est_time_perfect_clk(input_off_times)
        if self.time_units == "ms":
            est_off_times = np.round(np.multiply(est_off_times, 1000))
        return int(est_off_times[0]), np.asarray(clock_dead_periods, dtype=object)[0], self.max_meas_time*1000