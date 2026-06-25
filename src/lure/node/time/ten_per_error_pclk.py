from lure.config.configuration import Config
from lure.node.time.persistent_clock import PersistentClock

import numpy as np
import random


class TenPerPersistentClock(PersistentClock):
    def __init__(self, config: Config):
        super().__init__(config)
        self.max_meas_time = 50

    def get_uniform_estimation_offtime(self, input_number, percent_error):
        """
        The function `get_uniform_estimation_offtime` calculates error limits based on a percentage and
        generates a random number within that range.

        :param input_number: The input number is the value for which you want to estimate the off-time. It
        is the central value around which the estimation will be made
        :param percent_error: The `percent_error` parameter represents the percentage of error allowed in
        the estimation. It is used to calculate the error limits for the estimation
        :return: a random number within the range defined by the lower_limit and upper_limit.
        """
        # Calculate the error limits based on the percentage
        error = input_number * (percent_error / 100)
        lower_limit = input_number - error
        upper_limit = input_number + error

        # Generate a random number within the range
        return random.uniform(lower_limit, upper_limit)

    def get_oneD_estimation_offtime(self, input_number, percent_error):
        """
        The function `get_oneD_estimation_offtime` calculates error limits based on a percentage and
        generates a random number within that range.

        :param input_number: The input number is the value for which you want to generate an estimation. It
        is the central value around which the estimation will be generated
        :param percent_error: The `percent_error` parameter is the percentage of error allowed in the
        estimation. It determines the range within which the estimated value can vary from the input number
        :return: a random number within the range of the input number and its upper limit.
        """
        # Calculate the error limits based on the percentage
        error = input_number * (percent_error / 100)
        input_number - error
        upper_limit = input_number + error

        # Generate a random number within the range
        return random.uniform(input_number, upper_limit)

    def est_time_error_clk(self, input_off_times):
        """
        The function `est_time_error_clk` takes a list of input off times, calculates estimated off times
        based on a maximum measurement time, and determines if there are any clock dead periods.

        :param input_off_times: The parameter "input_off_times" is a list of time values representing the
        off times of a clock
        :return: two lists: est_off_times and clock_dead_periods.
        """
        clock_dead_periods = []
        est_off_times = []
        for offtime in input_off_times:
            if offtime <= self.max_meas_time:
                est_off_times.append(self.get_uniform_estimation_offtime(offtime, 10))
                clock_dead_periods.append(False)
            else:
                est_off_times.append(self.max_meas_time)
                clock_dead_periods.append(True)

        return est_off_times, clock_dead_periods

    def get_est_offtimes(self, input_off_time):
        """
        The function `get_est_offtimes` converts input off times from milliseconds to seconds if necessary,
        estimates the time error and clock dead periods, and returns the estimated off times, clock dead
        periods, and maximum measurement time in milliseconds.

        :param input_off_time: The `input_off_time` parameter is a single value representing the off time
        :return: three values:
        1. The estimated off time (as an integer)
        2. The clock dead periods (as a numpy array)
        3. The maximum measurement time (converted to us)
        """
        input_off_times = []
        if self.time_units == "ms":
            input_off_times.append(np.divide(input_off_time, 1000))
        # Get voltage from the off time for test data
        est_off_times, clock_dead_periods = self.est_time_error_clk(input_off_times)
        if self.time_units == "ms":
            est_off_times = np.round(np.multiply(est_off_times, 1000))
        return (
            int(est_off_times[0]),
            np.asarray(clock_dead_periods, dtype=object)[0],
            self.max_meas_time * 1000,
        )
