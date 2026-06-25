from lure.config.configuration import Config
from lure.node.time.continuous_time import ContinuousTimeModule
from lure.node.net.packet import Packet, PacketType
from lure.node.stats import Stats, StatType, StatsProvider

from sklearn.linear_model import LinearRegression
from collections import deque
import numpy as np
from enum import Enum


class LeveePacketKeys(Enum):
    TS_KEY = "timestamp"
    SEQ_NUM_KEY = "seq_num"
    ROOT_ID_KEY = "root_id"


class SSTLeveeTimeModule(ContinuousTimeModule):
    def __init__(self, config: Config):
        super().__init__(config)
        self.reg_table_size = None
        self.root_timeout = None
        self.sync_period = None
        self.reg_table_size = None
        self.dead_period_window = None
        self.max_ontimes_to_send_ts = None
        config.extract("reg_table_size", self, 10)
        config.extract("root_timeout", self, 100000)
        config.extract("sync_period", self, 30000)
        config.extract("reg_table_size", self, 10)
        config.extract("dead_period_window", self, 5)
        config.extract("max_ontimes_to_send_ts", self, 5)
        self.est_shared_time = 0
        self.no_dead_period_time = []
        # list to save history of clock dead periods
        self.clk_dead_periods = deque([], maxlen=self.dead_period_window)
        self.TS_KEY = "ref_time"
        # number of dead periods since last timestamp from reference node
        self.sum_ontimes_dead_period = 0
        self.num_dead_periods = 0
        self.ref_time = deque([], maxlen=self.reg_table_size)
        self.loc_time = deque([], maxlen=self.reg_table_size)
        # tables to track time when there is no clock dead period
        self.ref_time_no_dead = deque([], maxlen=self.reg_table_size)
        self.loc_time_no_dead = deque([], maxlen=self.reg_table_size)
        self.prev_ontime = 0
        self.cont_local_time_no_levee = 0
        self.last_ts_time = 0
        self.highest_seq_num = 1
        self.num_comms = 0
        self.my_root_id = None
        self.time_to_sync = 0

    # Returns best guess of reference time - shared sense of time
    def time(self) -> int:
        return self.est_shared_time

    # Called on node boot. t is the ground truth time that the node was off.
    def boot(self, t: int):
        """
        The "boot" function in Python increments counters and calculates time values based on whether there
        is a clock dead period or not.

        :param t: The parameter "t" in the "boot" method represents the current off-time.
        :type t: int
        """
        super().boot(t)
        # if there is a clock dead period
        if self.is_dead_period:
            self.num_dead_periods += 1
            self.sum_ontimes_dead_period += self.last_ontime
            self.debug(
                f"Node {self.node_id} encountered clock dead period, offtime: {t}, pclk time: {self.last_pclk_est}"
            )
        else:
            self.no_dead_period_time.append(self.prev_ontime + self.last_pclk_est)
            self.cont_local_time += self.last_pclk_est
            self.est_shared_time += self.last_pclk_est

        # Update local time that would not be affected by Levee
        self.cont_local_time_no_levee += self.last_pclk_est

        # Estimate reference time on each boot
        self.est_shared_time = self.est_ref_time_reg()
        self.stats.time_series_append(StatType.EST_SHARED_TIME, self.est_shared_time)
        self.stats.time_series_append(StatType.CONT_LCL_TIME, self.cont_local_time)

        if (
            self.my_root_id != self.node_id
            and (self.est_shared_time - self.last_ts_time >= self.root_timeout)
        ) or (self.my_root_id is None):
            self.my_root_id = self.node_id
            self.debug(f"Root timeout: Node {self.node_id} becomes root!")
            self.root_timeout_start = self.timestepper.simpy_env.now

    def execute(self):
        """
        The function updates the clock and calculates the estimated shared time of a node.
        """
        if self._last_update is not None:
            executed_time = self.timestepper.simpy_env.now - self._last_update
            # Updates the clock for a given amount
            updated_clock = self.active_clock.update(executed_time)
            self.est_shared_time += updated_clock
            self.cont_local_time += updated_clock
            self.cont_local_time_no_levee += updated_clock
        self._last_update = self.timestepper.simpy_env.now
        # Fetch estimated shared time of the node at Tm, if it's on
        if self.timestepper.simpy_env.now % 10000 == 0:
            self.stats.time_series_append(
                StatType.EST_SHARED_TIME_TM, self.est_shared_time
            )

    # Called for every outgoing packet. Use this to add headers, e.g. time info, to the packet.
    def frame(self, packet: Packet) -> bool:
        """
        This function sends a packet with timestamp, sequence number, and root ID if certain conditions are met.
        :param packet: The "packet" parameter is an instance of the "Packet" class, which is being passed as
        an argument to the "frame" method. The method is using this packet to set some header fields and
        send it to other nodes in the network
        :type packet: Packet
        :return: The function `frame` returns a boolean value. It returns `True` if the packet is needed to be sent, and `False` otherwise.
        """
        # Execute to update cont local and shared time
        self.execute()
        num_entries = len(self.ref_time)
        # Set packet headers
        packet.set_header(LeveePacketKeys.TS_KEY, self.est_shared_time, 4)
        packet.set_header(LeveePacketKeys.SEQ_NUM_KEY, self.highest_seq_num, 4)
        packet.set_header(LeveePacketKeys.ROOT_ID_KEY, self.my_root_id, 4)
        # If I am the root node and There is time to send synchronization messages
        if self.my_root_id == self.node_id:
            if (self.est_shared_time - self.time_to_sync) > self.sync_period:
                self.debug(
                    f"Root Node {self.node_id} Sent Time Stamp {self.est_shared_time}"
                )
                self.highest_seq_num += 1
                self.stats.increment(StatType.PACKETS_SENT_TIME)
                return True
            else:
                return False
        # if node is not a root node, send timestamps asynchronously
        # send timestamps only when node's regression tables are maxed out or if node is the root node and it is time to send
        elif (
            (self.my_root_id != self.node_id)
            and (num_entries >= self.reg_table_size)
            and (self.num_ontimes_since_last_ts <= self.max_ontimes_to_send_ts)
        ):  # if a node is synchronized
            self.debug(f"Node {self.node_id} Sent Time Stamp {self.est_shared_time}")
            self.stats.increment(StatType.PACKETS_SENT_TIME)
            return True
        else:
            return False

    def parse(self, packet: Packet) -> bool:
        """
        This function parses a received packet and updates regression tables based on the contents of the packet.

        :param packet: The packet parameter is an instance of the Packet class, which contains information
        about the message being received, such as its headers and payload
        :type packet: Packet
        :return: a boolean value. If the received timestamp is None, it returns False. If the message's root
        ID is less than the node's root ID, it updates the node's root ID and returns False. If the
        message's root ID is greater than the node's root ID or the message's sequence number is less than
        or equal to the node's highest sequence number, it returns False
        """
        # Execute to update cont local and shared time
        self.execute()
        msg_root_id = packet.pop_header(LeveePacketKeys.ROOT_ID_KEY)
        msg_root_seq_num = packet.pop_header(LeveePacketKeys.SEQ_NUM_KEY)
        received_ts = packet.pop_header(LeveePacketKeys.TS_KEY)

        # Update time to synchronize
        if self.est_shared_time >= self.time_to_sync + self.sync_period + 5000:
            self.time_to_sync += self.sync_period
            self.debug(f"Time to sync period updated to {self.time_to_sync}")

        # In case node recieves a timestamp before it declares itself as root node
        if self.my_root_id is None:
            self.my_root_id = self.node_id

        if (
            received_ts is None or packet.type == PacketType.ACK
        ):  # if received an acknowledgement
            return False
        elif (
            msg_root_id < self.my_root_id
        ):  # if received root id is less than my root id
            if self.node_id == self.my_root_id:
                self.debug(f"Node {self.node_id} removed as root")
                self.total_time_as_root += (
                    self.timestepper.simpy_env.now - self.root_timeout_start
                )
                self.stats.time_series_append(
                    StatType.ROOT_TIMEOUT,
                    [self.root_timeout_start, self.timestepper.simpy_env.now],
                )
                self.stats.set(
                    StatType.NODE_TOTAL_ROOT_TIMEOUT, self.total_time_as_root
                )
                self.stats.increment(StatType.PACKETS_RECEIVED_TIME)
            self.my_root_id = msg_root_id
        elif (
            msg_root_id > self.my_root_id or msg_root_seq_num <= self.highest_seq_num
        ):  # manages redundant information
            self.stats.increment(StatType.PACKETS_RECEIVED_TIME)
            return False
        else:
            return False

        # Update highest seq_num. It is used to manage redundant information that we get from the nodes
        self.highest_seq_num = msg_root_seq_num

        self.add_entry_and_estimate_drift(received_ts, packet)
        self.num_comms += 1
        return True

    def add_entry_and_estimate_drift(self, received_ts, packet):
        """
        The function `add_entry_and_estimate_drift` updates the local and shared time, estimates the
        drift in time, executes the levee mechanism to estimate dead periods, updates the local and
        reference time tables, and appends communication data to a time series statistics object.

        :param received_ts: The parameter `received_ts` represents the timestamp received from a packet.
        It is the timestamp at which the packet was received
        :param packet: The "packet" parameter is an object that represents the received packet. It
        contains information such as the source ID of the packet and the timestamp of when it was
        received
        """
        total_time_lost = 0
        # Execute to update cont local and shared time
        self.execute()
        self.debug(
            f"Received TS: {received_ts} from node {packet.source_id}, shared time: {self.est_shared_time}, last comm shared time: {self.get_last_comm_shared_time()}, local time: {self.cont_local_time}, local time FTSP: {self.cont_local_time_no_levee}"
        )
        # Add packet transmit timeout to received time
        self.transmit_timeout = (
            self.netstack.slot_length
            - self.netstack.slot_length * self.netstack.mac.ack_fraction
        )
        received_ts += self.transmit_timeout

        # Get time difference since last handshake from neighbor shared sense of time
        time_from_last_timestamp = received_ts - self.get_last_comm_shared_time()
        time_wo_dp = self.get_adj_time_wo_dead_periods()
        self.debug(
            f"time diff from last comm:  {time_from_last_timestamp}, time wo dp: {time_wo_dp}"
        )

        # Execute levee mechanism
        if self.num_dead_periods > 0:
            # Get estimate of dead periods and save it to the list
            total_time_lost = time_from_last_timestamp - time_wo_dp
            est_dead_period = total_time_lost / self.num_dead_periods
            self.clk_dead_periods.append(est_dead_period)

            self.debug(
                f"Total time lost: {total_time_lost}, Estimated dead periods time: {est_dead_period}, Clk dead periods: {self.clk_dead_periods}, num dead periods: {self.num_dead_periods}, sum of on-times: {self.sum_ontimes_dead_period}"
            )

            # Update local time
            if self.num_comms > 2:
                self.cont_local_time += total_time_lost
                self.debug(
                    f"Updated local time by  estimated {total_time_lost} for node {self.node_id}"
                )

            # Estimate time using levee
            self.est_shared_time += self.est_time_levee(time_wo_dp)
        else:
            self.ref_time_no_dead.append(received_ts)
            self.loc_time_no_dead.append(self.cont_local_time)

        # clear no clock dead period time
        self.is_dead_period = False
        self.no_dead_period_time = []
        self.num_dead_periods = 0
        self.sum_ontimes_dead_period = 0

        # Estimate shared time
        self.execute()
        self.est_shared_time = self.est_ref_time_reg()

        # Update local/Reference time tables
        self.ref_time.append(received_ts)
        self.loc_time.append(self.cont_local_time)

        # append successful communication data to time series stat object
        self.stats.time_series_append(
            StatType.SUCC_COMM,
            [packet.source_id, self.node_id, received_ts, self.est_shared_time],
        )
        self.stats.time_series_append(StatType.EST_SHARED_TIME, self.est_shared_time)
        # Update time stamp time
        self.last_ts_time = self.est_shared_time
        self.num_ontimes_since_last_ts = 0

    def get_skew_no_dead_period(self):
        """
        The function returns the skew value without dead periods, which is calculated based on the linear regression parameters
        of the given location and reference times.
        :return: the value of the variable "beta".
        """
        if len(self.loc_time_no_dead) > 2:
            beta, _ = self.get_lr_params(self.loc_time_no_dead, self.ref_time_no_dead)
        else:
            beta = 1
        return beta

    # Return predicted clock dead periods from the history of dead periods
    def predict_dead_period(self):
        """
        The function `predict_dead_period` calculates the predicted dead period based on the average of the
        clock dead periods.
        :return: the predicted dead period.
        """
        if len(self.clk_dead_periods) < 1:
            # TODO: update with real max PCLK duration
            predicted_dead_period = self.max_meas_time
        else:
            predicted_dead_period = np.mean(self.clk_dead_periods)
        return predicted_dead_period

    # Returns fitted linear regression model
    def fit_linear_reg(self, xdata, ydata):
        """
        The function `fit_linear_reg` fits a linear regression model to the given data.

        :param xdata: xdata is the input data for the independent variable(s) in the linear regression
        model. It should be a 1-dimensional array-like object, such as a list or a NumPy array
        :param ydata: The `ydata` parameter represents the dependent variable or the target variable in a
        linear regression model. It is the variable that we are trying to predict or explain using the
        independent variable(s) `xdata`
        :return: a linear regression model that has been fitted to the given xdata and ydata.
        """
        xdata_reshape = np.reshape(xdata, (-1, 1))
        ydata = np.asarray(ydata, dtype=object)
        reg_model = LinearRegression().fit(xdata_reshape, ydata)
        return reg_model

    # Returns alpha and beta parameters of Linear regression
    def get_lr_params(self, xdata, ydata):
        """
        The function "get_lr_params" fits a linear regression model to the given data and returns the slope
        (alpha) and intercept (beta) of the fitted line.

        :param xdata: The xdata parameter is the input data used for training the linear regression model.
        It represents the independent variables or features that are used to predict the dependent variable
        or target variable (ydata)
        :param ydata: The dependent variable or the target variable. It is the variable that we are trying
        to predict or explain using the independent variables
        :return: the values of alpha and beta, which are the coefficients of the linear regression model.
        """
        reg_model = self.fit_linear_reg(xdata, ydata)
        beta = reg_model.intercept_
        alpha = reg_model.coef_
        return alpha[0], beta

    # Returns the estimated reference clock time using the least squares method
    def get_ref_time_estimate(self, xdata, ydata, x):
        """
        The function `get_ref_time_estimate` uses linear regression to estimate a y-value for a given
        x-value.

        :param xdata: The xdata parameter is a list or array containing the independent variable values. It
        represents the input data for the regression model
        :param ydata: The ydata parameter represents the dependent variable or the target variable in the
        linear regression model. It is the variable that we are trying to predict or estimate based on the
        given xdata
        :param x: The parameter `x` represents the input value for which you want to estimate the reference
        time
        :return: the predicted value for the given input 'x' using the linear regression model.
        """
        reg_model = self.fit_linear_reg(xdata, ydata)
        pred = reg_model.predict(np.array([[x]], dtype=object))
        return pred[0]

    # Returns the estimated time using linear regression
    def est_ref_time_reg(self):
        """
        The function `est_ref_time_reg` returns an estimated time based on the reference time and local
        time.
        :return: the estimated time.
        """
        if len(self.ref_time) > 2:
            est_time = self.get_ref_time_estimate(
                self.loc_time, self.ref_time, self.cont_local_time
            )
        else:
            est_time = self.cont_local_time
        return est_time

    # Estimate reference time using Levee mechanism
    def est_time_levee(self, est_ref_time_wo_dead_periods):
        """
        The function calculates the estimated off-time, taking into account any dead periods.

        :param est_ref_time_wo_dead_periods: est_ref_time_wo_dead_periods is the estimated reference time
        without considering any dead periods. It is the base time that is used to calculate the estimated
        time
        :return: the estimated shared time.
        """
        if self.num_dead_periods > 0:
            est_time = (
                est_ref_time_wo_dead_periods
                + (self.num_dead_periods * self.predict_dead_period())
                + self.sum_ontimes_dead_period
            )
        else:
            est_time = self.est_ref_time_reg()
        return est_time

    # Returns adjusted no clock dead period time
    def get_adj_time_wo_dead_periods(self):
        """
        The function calculates the adjusted time without any clock dead periods, taking into account the
        skew.
        :return: the adjusted time without any clock dead periods.
        """
        # total time of no clock dead period
        total_time_wo_dead_period = np.sum(self.no_dead_period_time)
        # correction with skew
        adj_time_wo_dead_period = (
            total_time_wo_dead_period * self.get_skew_no_dead_period()
        )
        return adj_time_wo_dead_period

    # Return last communication time of reference
    def get_last_comm_shared_time(self):
        """
        The function `get_last_comm_shared_time` returns the last communication reference time from a list,
        or 0 if the list is empty.
        :return: the last element in the list `self.ref_time` if the list is not empty. If the list is
        empty, it returns 0.
        """
        if len(self.ref_time) < 1:
            last_comm_ref_time = 0
        else:
            last_comm_ref_time = self.ref_time[-1]
        return last_comm_ref_time

    # Return last local communication time
    def get_last_comm_local_time(self):
        """
        The function `get_last_comm_local_time` returns the last element in the `loc_time` list if it
        exists, otherwise it returns 0.
        :return: the last element in the `self.loc_time` list.
        """
        if len(self.loc_time) < 1:
            last_local_time = 0
        else:
            last_local_time = self.loc_time[-1]
        return last_local_time

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.active_clock.stats = stats
        self.persistent_clock.stats = stats

        self.stats.register_time_series(StatType.SUCC_COMM)
