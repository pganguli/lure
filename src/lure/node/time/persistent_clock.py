from typing import Tuple
from lure.config.configuration import Config
from lure.node.time.clock import Clock

import pickle
import numpy as np
from collections import deque
from scipy import optimize
from abc import ABC, abstractmethod
import random
import os
    
class PersistentClock(Clock, ABC):     
    def __init__(self, config: Config):
        super().__init__(config)
        self.t = 0
        self.time_units = "ms"
        # Number of channels in the pclk
        self.num_channels = 6
        # Component Clock time measurement range in seconds
        self.clk_range = [200, 250, 0.5, 0.5, 10, 50]
        # Get experiment data from pickle file
        self.exp_data = self.unpickle_data(os.path.dirname(os.path.realpath(__file__)) + "/pclk_exp_data.pickle")
        # Create map tables
        self.map_tables = self.create_map_tables()

    @abstractmethod
    def get_est_offtimes(self, input_off_time: int) -> Tuple[int, bool, int]:
        """
        The function `get_est_offtimes` takes an input off time and returns a tuple containing three values:
        an integer, a boolean, and another integer.
        
        :param input_off_time: The input_off_time parameter is an integer that represents the off-time
        :type input_off_time: int
        """
        pass

    def unpickle_data(self, path):
        """
        The function `unpickle_data` takes a file path as input, opens the file in binary mode, unpickles
        the data from the file, closes the file, and returns the unpickled data.
        
        :param path: The path parameter is a string that represents the file path of the pickled file that
        you want to unpickle and load
        :return: the unpickled data.
        """
        pickled_file = open(path, "rb")
        unpickled_data = pickle.load(pickled_file)
        pickled_file.close()
        return unpickled_data

    def cap_discharge_func(self, t, v0, RC):
        """
        The function calculates the voltage of a capacitor during a discharge process.
        
        :param t: The parameter "t" represents time. It is the independent variable in the function and is
        used to calculate the voltage at a given time
        :param v0: The initial voltage at time t=0
        :param RC: RC is the time constant of the RC circuit. It is the product of the resistance (R) and
        the capacitance (C) in the circuit. The time constant represents the time it takes for the voltage
        across the capacitor to reach approximately 63.2% of its final value during a discharge
        :return: the value of `v0` multiplied by `e` raised to the power of `-t/RC`.
        """
        return v0 * np.exp(np.divide(-t, RC))

    def create_map_table_fit(self, mean_map_table):
        """
        The function `create_map_table_fit` takes a mean map table as input, fits a curve to the data, and
        returns a new map table with the fitted curve.
        
        :param mean_map_table: The `mean_map_table` parameter is a 3-dimensional numpy array that represents
        the mean map table. It has the shape `(num_channels, num_points, 2)`, where:
        :return: a numpy array called `map_table_fit`.
        """
        map_table_fit = deque([])
        for channel in range(self.num_channels):
            voltage = mean_map_table[channel][:,0]
            time = mean_map_table[channel][:,1]
            params, _ = optimize.curve_fit(self.cap_discharge_func, time, voltage)
            time = np.linspace(0, self.clk_range[channel], 500)
            volt = self.cap_discharge_func(time, params[0], params[1])
            map_table_fit.append([volt, time])

        map_table_fit = np.asarray(map_table_fit)
        map_table_fit = np.swapaxes(map_table_fit, 1, 2)
        return map_table_fit

    def slice_map_tables(self, map_table_fit, num_off_times, discharge_volts=0.5):
        """
        The function `slice_map_tables` takes a map table fit, the number of off times, and an optional
        discharge voltage as input, and returns a modified map table that only includes data up until the
        capacitor is discharged.
        
        :param map_table_fit: The variable `map_table_fit` is a fit of the map table data. It is likely a 2D
        array or matrix where each row represents a channel and each column represents a different parameter
        or measurement
        :param num_off_times: The parameter "num_off_times" represents the number of off times for each
        channel in the map table
        :param discharge_volts: The `discharge_volts` parameter is the voltage threshold at which a
        capacitor is considered discharged. If the voltage of a capacitor at a certain off time is below
        this threshold, it is considered discharged
        :return: the variable "map_table_discharged", which is a numpy array containing the voltage and time
        data for each channel after discharging.
        """
        mean_map_table = map_table_fit
        map_table_discharged = deque([])
        volt_discharged = deque([])
        for channel in range(self.num_channels):  
            for off_time_idx in range(num_off_times):
                # check if capacitor is discharged?
                if (mean_map_table[channel][:,0][off_time_idx] < discharge_volts):
                    volt_discharged.append([channel, mean_map_table[channel][:,0][off_time_idx],off_time_idx])
                    voltage = mean_map_table[channel][:,0][0: off_time_idx]
                    time = mean_map_table[channel][:,1][0: off_time_idx]
                    map_table_discharged.append([voltage, time])
                    break
                elif (off_time_idx == (num_off_times-2)):
                    voltage = mean_map_table[channel][:,0][0: off_time_idx]
                    time = mean_map_table[channel][:,1][0: off_time_idx]
                    map_table_discharged.append([voltage, time])
                    break

        volt_discharged = np.asarray(volt_discharged, dtype=object)
        map_table_discharged = np.asarray(map_table_discharged,dtype=object)
        return map_table_discharged

    def create_map_tables(self):        
        """
        The function `create_map_tables` generates map tables based on experimental data, takes the average
        of all experiments, fits a curve to the map table, and slices the map tables to discharge points.
        :return: the variable "map_tables", which is a list of map tables.
        """
        num_exp = self.exp_data.shape[0]
        off_times = self.exp_data[0][:,0]
        map_table_channel = deque([])
        map_table = deque([])
        map_table_exp = deque([])
        for exp_num in range(num_exp):
            for channel in range(self.num_channels):
                for off_time_idx in range(len(off_times)):
                    voltage = self.exp_data[exp_num][off_time_idx][2][channel][0]
                    map_table_channel.append([voltage, off_times[off_time_idx]])
                map_table.append(map_table_channel)
                map_table_channel = deque([])
            map_table_exp.append(map_table)
            map_table = deque([])

        num_off_times = off_times.shape[0]
        map_table_exp = np.asarray(map_table_exp)
        # Take average of all experiments
        mean_map_table = np.mean(map_table_exp, axis=0)
        # generate a curve fitted map table, cut-off at discharge points
        map_table_fit = self.create_map_table_fit(mean_map_table)
        # Slice map tables to discharge points
        map_tables = self.slice_map_tables(map_table_fit, num_off_times)    
        return map_tables

    def linear_extrapolation(self, x0, y0, x1, y1, x):
        """
        The function performs linear extrapolation to estimate the value of y for a given x, based on two
        known points (x0, y0) and (x1, y1).
        
        :param x0: The x-coordinate of the first known point on the line
        :param y0: The initial value of y at x0
        :param x1: The x-coordinate of the second point on the line
        :param y1: The value of the dependent variable (y) at the second data point (x1)
        :param x: The parameter `x` represents the x-coordinate for which you want to calculate the
        corresponding y-coordinate using linear extrapolation
        :return: the value of y, which is the result of linear extrapolation based on the given inputs.
        """
        y = y0 + ((x-x0)/(x1-x0))*(y1-y0)
        return y

    def find_slope(self, y1, x1, y0, x0):
        """
        The function calculates the slope between two points on a graph.
        
        :param y1: The y-coordinate of the second point on the line
        :param x1: The x-coordinate of the second point
        :param y0: The y-coordinate of the first point on the line
        :param x0: The x-coordinate of the first point
        :return: The slope of the line passing through the points (x0, y0) and (x1, y1).
        """
        slope = (y1-y0)/(x1-x0)
        return slope

    def findTimeAndSlope(self, time_arr, volt_arr, input_volts):
        """
        The function `findTimeAndSlope` takes in arrays of time and voltage values, as well as an input
        voltage, and returns the predicted time, slope, time difference, and positive/negative time
        differences based on linear extrapolation or interpolation.
        
        :param time_arr: The time_arr parameter is a list or array that contains the time values
        corresponding to the voltage values in the volt_arr parameter. It represents the time values at
        which the voltage measurements were taken
        :param volt_arr: The `volt_arr` parameter is an array that contains voltage values
        :param input_volts: The input voltage for which we want to find the corresponding time and slope
        :return: The function `findTimeAndSlope` returns multiple values: `pred_time`, `slope`, `td`,
        `ts_pos_diff`, and `ts_neg_diff`.
        """
        if input_volts > volt_arr[0]:
            pred_time = self.linear_extrapolation(volt_arr[0], time_arr[0], volt_arr[1], time_arr[1], input_volts)   
            slope = self.find_slope(volt_arr[0], time_arr[0], volt_arr[1], time_arr[1])
            # Time can't be negative
            if pred_time < 0:
                pred_time = 0
            td = time_arr[0] # time difference between the mapping table times for interpolation/bin size
            ts_pos_diff = time_arr[0]
            ts_neg_diff = time_arr[0]
        
        # When input voltage is less than last entry in mapping table
        elif input_volts < volt_arr[-1]:
            pred_time = time_arr[-1]
            td = time_arr[-1]
            slope = 0
            ts_pos_diff = 0
            ts_neg_diff = 0
        # If time exactly matches in one of the entry of mapping table
        elif np.shape(volt_arr[np.where(volt_arr==input_volts)])[0] > 0:
            matched_voltage = volt_arr[np.where(volt_arr==input_volts)][0]
            matched_idx = np.where(volt_arr==matched_voltage)[0][0]
            pred_time = time_arr[matched_idx] 
            td = time_arr[matched_idx] 
            if input_volts == volt_arr[-1]:
                slope = 0
            else:
                slope = self.find_slope(volt_arr[matched_idx], time_arr[matched_idx], volt_arr[matched_idx-1], time_arr[matched_idx-1])
            ts_pos_diff = 0
            ts_neg_diff = 0
        # If input voltage is in between then do interpolation        
        else: 
            try:
                idx = np.where(volt_arr<input_volts)[0][0] -1
                pred_time = np.interp(input_volts, [volt_arr[idx], volt_arr[idx+1]], [time_arr[idx], time_arr[idx+1]])
                slope = self.find_slope(volt_arr[idx], time_arr[idx], volt_arr[idx+1], time_arr[idx+1])
                td = time_arr[idx+1] - time_arr[idx]
                ts_pos_diff = pred_time - time_arr[idx+1]
                ts_neg_diff = pred_time - time_arr[idx]
            except:
                self.error("Can not find time and slope at Idx: ", idx)

        return pred_time, slope, td, ts_pos_diff, ts_neg_diff

    def cal_est_times(self): 
        """
        The function `cal_est_times` calculates the estimated time for each channel at each off-time and all
        experiment samples.
        :return: two values: est_time_exp, which is a numpy array containing the estimated time for each
        channel at each off-time and all experiment samples, and num_exp, which is the number of
        experiments.
        """
        est_time_channels = deque([])
        est_time_offtime = deque([])
        est_time_exp = deque([])
        num_off_times = self.exp_data[0][:,0].shape[0]
        num_channels = self.exp_data[0][:,2][0].shape[0]
        num_exp = self.exp_data.shape[0]

        # Find estimated time for each channel at each off-time and all experiment samples
        for exp in range(num_exp):
            for off_time_idx in range(num_off_times):
                for channel in range(num_channels):
                    voltage = self.exp_data[exp][off_time_idx][2][channel][0]
                    time_arr = np.round(self.map_tables[channel][1], decimals=6)
                    volt_arr = np.round(self.map_tables[channel][0], decimals=6)
                    est_time, _, td, ts_pos_diff, ts_neg_diff = self.findTimeAndSlope(time_arr, volt_arr, voltage)
                    est_time = np.round(est_time, decimals=6)
                    est_time_channels.append(est_time)
                est_time_offtime.append(est_time_channels)
                est_time_channels = deque([])
            est_time_exp.append(est_time_offtime)
            est_time_offtime = deque([])

        est_time_exp = np.asarray(est_time_exp)
        return est_time_exp, num_exp

    def linear_extra(self, x0, y0, x1, y1, x):
        """
        The function calculates the value of y for a given x using linear interpolation between two points
        (x0, y0) and (x1, y1).
        
        :param x0: The x-coordinate of the first point on the line
        :param y0: The initial value of y at x0
        :param x1: The x-coordinate of the second point on the line
        :param y1: The value of y at the point (x1, y1)
        :param x: The value of x for which you want to calculate the corresponding y value
        :return: the value of y, which is calculated using the linear interpolation formula.
        """
        y = y0 + ((x-x0)/(x1-x0))*(y1-y0)
        return y

    def get_volt_from_time(self, time_arr, volt_arr, off_time):
        """
        The function `get_volt_from_time` takes in arrays of time and voltage values, as well as an off
        time, and returns an estimated voltage based on linear interpolation or extrapolation.
        
        :param time_arr: The `time_arr` parameter is an array that contains the time values in the mapping
        table. It represents the time at which voltage measurements were taken
        :param volt_arr: The `volt_arr` parameter is an array that contains voltage values corresponding to
        each time entry in the `time_arr` parameter
        :param off_time: The parameter "off_time" represents the time at which the voltage needs to be
        estimated
        :return: the estimated voltage based on the given time array, voltage array, and off time.
        """
        # Check where input off_time is less than first entry in the table
        if off_time < time_arr[0]:
            est_voltage = self.linear_extra(time_arr[0], volt_arr[0], time_arr[1], volt_arr[1], off_time)   
        # When input off_time is greater than last entry in mapping table
        elif off_time > time_arr[-1]:
            est_voltage = volt_arr[-1]
        # If time exactly matches in one of the entry of mapping table
        elif np.shape(time_arr[np.where(time_arr==off_time)])[0] > 0:
            est_voltage = volt_arr[np.where(time_arr==off_time)][0]
        else:
        # If input off time is in between then do interpolation 
            idx = np.where(time_arr>off_time)[0][0] - 1
            est_voltage = np.interp(off_time, [time_arr[idx], time_arr[idx+1]], [volt_arr[idx], volt_arr[idx+1]]) 
            
        return est_voltage

    def get_channel_voltages(self, channel):
        """
        The `get_channel_voltages` function takes in a channel number and returns the sorted channel
        voltages, corresponding times, and the maximum measured voltage from a randomly selected experiment.
        
        :param channel: The `channel` parameter is the index of the channel for which you want to retrieve
        the voltages. It is used to access the specific channel voltage values in the `self.exp_data` array
        :return: The function `get_channel_voltages` returns three values: `sorted_channel_voltages`,
        `sorted_channel_times`, and `max_measured_voltage`.
        """
        channel_voltages = []
        channel_times = []
        # Find num of experiments
        num_exp = np.shape(self.exp_data)[0]
        # Randomly pick eperiment sample
        randExp = random.randint(0, num_exp-1)
        # iterate through all off times to get channel volts and time
        for offtime_idx in range(len(self.exp_data[randExp, :, 2])):
            channel_volt = self.exp_data[randExp, :, 2][offtime_idx][channel, 0]
            channel_time = self.exp_data[randExp, :, 0][offtime_idx]
            channel_voltages.append(channel_volt)
            channel_times.append(channel_time)

        # Sort in descending order
        sorted_ind = np.argsort(channel_voltages)
        sorted_ind_desc = sorted_ind[::-1]
        sorted_channel_voltages = [channel_voltages[i] for i in sorted_ind_desc]
        sorted_channel_times = [channel_times[i] for i in sorted_ind_desc]
        max_measured_voltage = np.max(sorted_channel_voltages)
        return np.asarray(sorted_channel_voltages, dtype=object), np.asarray(sorted_channel_times, dtype=object), max_measured_voltage

    def cal_est_time_from_offtime(self, input_offtimes, clk_type):
        """
        The function `cal_est_time_from_offtime` calculates estimated times based on input off-times and
        channel data.
        
        :param input_offtimes: The input_offtimes parameter is a list of off times for each channel. It
        represents the time at which each channel is turned off
        :param clk_type: The `clk_type` parameter is a string that specifies the type of clock. It can
        have two possible values: "harc-lite" or "harc-naive"
        :return: multiple values:
        1. est_time_ip_offtimes: A numpy array containing the estimated times for each channel and each
        input offtime.
        2. sel_est_times: An array containing the selected estimated times for each input offtime.
        3. max_meas_allchannels_allofftimes: A numpy array indicating whether the estimated time for
        each channel and each input offtime is greater than or equal
        """
        est_time_channels = deque([])
        est_time_ip_offtimes = deque([])
        channels_slope = deque([])
        sel_est_times = deque([])
        hlite_max_meas_channels = []
        hlite_max_meas_allchannels_allofftimes = []
        discharge_idx_channel = []

        idx = -1
        for off_time in input_offtimes:
            discharge_idx_channel = []
            for channel in range(self.num_channels):
                time_arr = np.round(self.map_tables[channel][1], decimals=6)
                volt_arr = np.round(self.map_tables[channel][0], decimals=6)
                
                if channel == 4:
                    dischargeVoltage = 0.8
                    idx = np.where(volt_arr < dischargeVoltage)[0][0]
                    volt_arr = volt_arr[0:idx]
                    time_arr = time_arr[0:idx]
                    discharge_idx_channel.append(idx)
                else:
                    discharge_idx_channel.append(-1)

                channel_voltages, channel_times, max_meas_voltage = self.get_channel_voltages(channel)
                est_voltage = self.get_volt_from_time(channel_times, channel_voltages, off_time)
                pred_time, slope, td, tsPosDiff, tsNegDiff = self.findTimeAndSlope(time_arr, volt_arr, est_voltage)
                pred_time = np.round(pred_time, decimals=6)
                est_time_channels.append(pred_time)
                channels_slope.append(slope)
            est_time_ip_offtimes.append(est_time_channels)
            channels_slope = np.asarray(channels_slope)

            max_meas_time_hlite = np.round(self.map_tables[1][1], decimals=6)[-1]
            if clk_type == 'harc-lite':
                if np.all((channels_slope == 0)):
                    best_est_time = max_meas_time_hlite
                    hlite_max_meas_channels.append(True)
                else:
                    best_est_time = est_time_channels[np.argmin(channels_slope)]
                    hlite_max_meas_channels.append(False)
            elif clk_type == 'harc-naive':
                best_est_time = np.mean(est_time_channels)
            sel_est_times.append(best_est_time)
            hlite_max_meas_allchannels_allofftimes.append(np.asarray(hlite_max_meas_channels, dtype=object))
            est_time_channels = deque([])
            channels_slope = deque([])
            hlite_max_meas_channels = []

        est_time_ip_offtimes = np.asarray(est_time_ip_offtimes)
        sel_est_times = np.array(sel_est_times)

        # check if the estimated time is greater than or equal to max time
        # TODO: find max measurable time of HARC-reg
        max_meas_channels = []
        max_meas_allchannels_allofftimes = []
        for est_time in est_time_ip_offtimes:
            for channel, time in enumerate(est_time):
                if (time >= np.round(self.map_tables[channel][1], decimals=6)[discharge_idx_channel[channel]-1]):
                    max_meas_channels.append(True)
                else:
                    max_meas_channels.append(False)
            
            max_meas_allchannels_allofftimes.append(np.asarray(max_meas_channels, dtype=object))
            max_meas_channels = []
        
        max_meas_allchannels_allofftimes = np.asarray(max_meas_allchannels_allofftimes, dtype=object)
        
        return est_time_ip_offtimes, sel_est_times, max_meas_allchannels_allofftimes, hlite_max_meas_allchannels_allofftimes, max_meas_time_hlite