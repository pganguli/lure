import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
import numpy as np
from scipy.special import comb


class MetricAnalyzer:
    def __init__(self) -> None:
        pass

    """
        Initialize metric calculation parameters
    """

    def init_params(
        self,
        num_nodes,
        nodes_boot_events,
        nodes_die_events,
        nodes_succ_comm_events,
        nodes_time_tm10,
        metric_meas_period,
        sim_time,
    ):
        self.num_nodes = num_nodes
        self.nodes_boot_events = nodes_boot_events
        self.nodes_die_events = nodes_die_events
        self.nodes_succ_comm_events = nodes_succ_comm_events
        self.met_meas_period = metric_meas_period  # ms
        self.nodes_time_tm10 = (
            nodes_time_tm10  # nodes estimated ref time at each tm = 10, if it's on
        )
        self.sim_time = sim_time
        self.num_nodes_pairs = comb(self.num_nodes, 2, exact=True)

    def get_ontime_at_tm(self, node, meas_period):
        """
        The function `get_ontime_at_tm` returns the start and end times of on-periods for a given node where the measurement period lies inside the on-time.

        :param node: The "node" parameter represents a specific node in a system or network. It is used to identify and retrieve information related to that particular node
        :param meas_period: The `meas_period` parameter represents the measurement period for which we want to find the on-time of a node. It is a time period specified by a start time and an end time
        :return: a list of on-time periods for a given node where the measurement period lies inside the
        on-time. Each on-time period is represented as a list [ontime_start, ontime_end].
        """
        ontime_period = np.vstack(
            (self.nodes_boot_events[node][:, 0], self.nodes_die_events[node][:, 0])
        )
        node_ontime_tm = []
        # Iterate though all on times to find out if tm lies in on-period
        for idx in range(np.shape(ontime_period)[1]):
            overlap_idx = np.where(
                (meas_period > ontime_period[0][idx])
                & (meas_period < ontime_period[1][idx])
            )
            if np.shape(overlap_idx)[1] > 0:
                node_ontime_tm.append([ontime_period[0][idx], ontime_period[1][idx]])
        return node_ontime_tm

    def get_succ_comm_at_tm(self, node, node_ontime_tm):
        """
        The function `get_succ_comm_at_tm` takes a node and its on-time time range as input and returns a list of all successful communication times within that range.

        :param node: The `node` parameter represents a specific node in a network
        :param node_ontime_tm: The parameter `node_ontime_tm` is a 2D array that represents the on-time intervals for a node. Each row in the array represents a different on-time interval, and the first column represents the start time of the interval while the second column represents the end time of the interval
        :return: a list of all the successful communication times for a given node and its on-time
        intervals.
        """
        all_succ_comm_tms = []
        for on_idx in range(np.shape(node_ontime_tm)[0]):
            ontime_start = node_ontime_tm[on_idx][0]
            ontime_end = node_ontime_tm[on_idx][1]
            # For each on time check if succ communication lies in it
            # If there is any communication at all
            if len(self.nodes_succ_comm_events[node]) > 0:
                succ_comm_time = self.nodes_succ_comm_events[node][:, 0]
                succ_comm_tm = np.where(
                    (succ_comm_time > ontime_start) & (succ_comm_time < ontime_end)
                )
                # If it found communication at on times at Tm
                if len(succ_comm_tm[0]) > 0:
                    all_succ_comm_tms.append(succ_comm_tm[0])
        return all_succ_comm_tms

    def calc_pairwise_errors(self, nodes_error, contributing_nodes):
        """
        The function `calc_pairwise_errors` calculates the average error between pairs of nodes based on their error values.

        :param nodes_error: The `nodes_error` parameter is a list or array containing the error values for each node. Each element in the list represents the error value for a specific node
        :param contributing_nodes: The parameter "contributing_nodes" represents the number of nodes that are contributing to the calculation of pairwise errors
        :return: the average error among all the pairs of nodes.
        """
        nodes_error = np.array(nodes_error, dtype=object)
        nodes_error = np.divide(nodes_error, 1000)
        avg_error = 0
        if contributing_nodes < 2:
            avg_error = np.nan
        else:
            # Find all the pairs of nodes
            i, j = np.triu_indices(len(nodes_error), 1)
            # calculate average error among all the pairs of nodes
            error = np.abs(
                np.subtract(
                    np.nan_to_num(nodes_error[i]), np.nan_to_num(nodes_error[j])
                )
            )
            avg_error = np.nansum(error) / contributing_nodes
        return avg_error

    def calc_turnout_ratio(self, contributing, total):
        """
        The function calculates the turnout ratio by dividing the number of contributing elements by the total number of elements and multiplying the result by 100.

        :param contributing: The parameter "contributing" represents the number of people who contributed or participated in something
        :param total: The total parameter represents the total number of individuals or entities that are eligible to contribute or participate in some way
        :return: the turnout ratio, which is calculated by dividing the contributing value by the total value and then multiplying by 100.
        """
        return (contributing / total) * 100

    def get_met_meas_points(self):
        """
        The function `get_met_meas_points` returns a list of measurement points based on a given measurement period and simulation time.
        :return: a list of met_meas_points.
        """
        met_meas_points = []
        for met_meas_period in range(
            self.met_meas_period,
            self.sim_time + self.met_meas_period,
            self.met_meas_period,
        ):
            met_meas_points.append(met_meas_period)

        return met_meas_points

    def met_baseline(self):
        """
        The function `met_baseline` calculates the mean pairwise error, nodes turnout ratios, and pairs turnout ratios for a given measurement period for m_baseline metric.
        :return: three lists: m_baseline_errors, nodes_turnout_ratios, and pairs_turnout_ratios.
        """
        m_baseline_errors = []
        contributing_nodes = 0
        nodes_est_time = []
        nodes_turnout_ratios, pairs_turnout_ratios = [], []
        for met_meas_period in range(
            self.met_meas_period,
            self.sim_time + self.met_meas_period,
            self.met_meas_period,
        ):
            for node in range(self.num_nodes):
                if (np.shape(self.nodes_time_tm10[node])[0]) > 0:
                    # Find indices of all recorded time measurement at measurement period
                    succ_tm_ind = np.where(
                        self.nodes_time_tm10[node][:, 0] == met_meas_period
                    )[0]
                    if len(succ_tm_ind) > 0:
                        est_time = self.nodes_time_tm10[node][succ_tm_ind][:, 1][0]
                        nodes_est_time.append(est_time)
                        contributing_nodes += 1
                    else:
                        nodes_est_time.append(np.nan)
                else:
                    nodes_est_time.append(np.nan)

            # calculate pairwise error
            if any(not ele for ele in np.isnan(nodes_est_time)):
                error_mean = self.calc_pairwise_errors(
                    nodes_est_time, contributing_nodes
                )
            else:
                error_mean = np.nan
            m_baseline_errors.append(error_mean)
            nodes_est_time = []

            # Calculate turnout ratios
            nodes_turnout_ratios.append(
                self.calc_turnout_ratio(contributing_nodes, self.num_nodes)
            )
            pairs_turnout_ratios.append(
                self.calc_turnout_ratio(
                    comb(contributing_nodes, 2, exact=True), self.num_nodes_pairs
                )
            )
            contributing_nodes = 0

        return m_baseline_errors, nodes_turnout_ratios, pairs_turnout_ratios

    def met_handshake(self):
        """
        The function `met_handshake` calculates the pairwise errors, nodes turnout ratios, and pairs turnout ratios for a given measurement period for m_handshake.
        :return: three lists: m_handshake_errors, nodes_turnout_ratios, and pairs_turnout_ratios.
        """
        m_handshake_errors = []
        nodes_error = []
        contributing_nodes = 0
        contributing_nodes_pairs = []
        nodes_turnout_ratios, pairs_turnout_ratios = [], []

        for met_meas_period in range(
            self.met_meas_period,
            self.sim_time + self.met_meas_period,
            self.met_meas_period,
        ):
            # print("Met meas period: ", met_meas_period)
            for node in range(self.num_nodes):
                # Measurement period start and end time
                tm_start = met_meas_period - self.met_meas_period
                tm_end = met_meas_period
                # Check if there is any successful communication event
                if (np.shape(self.nodes_succ_comm_events[node])[0]) > 0:
                    # Find indices of all succ. comm. events within measurement period
                    succ_comm_ind = np.where(
                        (self.nodes_succ_comm_events[node][:, 0] > tm_start)
                        & (self.nodes_succ_comm_events[node][:, 0] <= tm_end)
                    )[0]
                    # If there are any events, calculate error
                    if len(succ_comm_ind) > 0:
                        succ_comm_events = self.nodes_succ_comm_events[node][:, 1][
                            succ_comm_ind
                        ]
                        succ_comm_events = np.array(
                            [np.array(xi, dtype=object) for xi in succ_comm_events]
                        )
                        sender_nodes = succ_comm_events[:, 0]
                        receiver_nodes = succ_comm_events[:, 1]
                        sender_time = succ_comm_events[:, 2]
                        receiver_time = succ_comm_events[:, 3]
                        # take error of only different time measurements
                        # TODO: Remove after fixing broadcast
                        diff_ind = np.where(sender_time != receiver_time)
                        if len(diff_ind[0]) > 0:
                            error = np.mean(
                                np.abs(
                                    np.subtract(
                                        sender_time[diff_ind], receiver_time[diff_ind]
                                    )
                                )
                            )
                        else:
                            error = 0
                        # error = np.mean(np.abs(np.subtract(sender_time, receiver_time)))
                        contributing_nodes += len(
                            list(
                                set(sender_nodes).symmetric_difference(
                                    set(receiver_nodes)
                                )
                            )
                        )
                        contributing_nodes_pairs.append(
                            list(
                                set(sender_nodes).symmetric_difference(
                                    set(receiver_nodes)
                                )
                            )
                        )
                    else:
                        error = np.nan
                else:
                    error = np.nan

                nodes_error.append(error)

            # Calculate turnout ratios
            contributing_nodes = len(
                list(
                    set(
                        [
                            item
                            for sublist in contributing_nodes_pairs
                            for item in sublist
                        ]
                    )
                )
            )
            # TODO: fix unique pairs calcualtion
            try:
                unique_pairs = np.unique(contributing_nodes_pairs, axis=0)
            except:
                unique_pairs = np.array([])
            num_cont_pairs = len(unique_pairs)
            nodes_turnout_ratios.append(
                self.calc_turnout_ratio(contributing_nodes, self.num_nodes)
            )
            pairs_turnout_ratios.append(
                self.calc_turnout_ratio(num_cont_pairs, self.num_nodes_pairs)
            )
            contributing_nodes = 0

            # If there is even one error measurement without nan value, then calculate pairwise errors
            # print(nodes_error)
            if any(not ele for ele in np.isnan(nodes_error)):
                pairwise_err = self.calc_pairwise_errors(nodes_error, num_cont_pairs)
            else:
                pairwise_err = np.nan

            # pairwise_err = self.calc_pairwise_errors(nodes_error, contributing_nodes)

            # print("Nodes pairwise err: ", pairwise_err)
            m_handshake_errors.append(pairwise_err)
            nodes_error = []
            contributing_nodes_pairs = []

        return m_handshake_errors, nodes_turnout_ratios, pairs_turnout_ratios

    def met_lifecycle(self):
        """
        Calculate the error of the network for each measurement period. Also calculate the turnout ratio of nodes that have successfully booted.
        @param self - the network itself
        @returns the error and the turnout ratio of nodes that have successfully booted.
        """
        m_lifecycle_errors = []
        nodes_error = []
        nodes_error_meas_period = []
        contributing_nodes = 0
        nodes_turnout_ratios, pairs_turnout_ratios = [], []
        for met_meas_period in range(
            self.met_meas_period,
            self.sim_time + self.met_meas_period,
            self.met_meas_period,
        ):
            for node in range(self.num_nodes):
                # Measurement period start and end time
                tm_start = met_meas_period - self.met_meas_period
                tm_end = met_meas_period
                # check if there is any boot event at all
                if (np.shape(self.nodes_boot_events[node][:, 0])[0]) > 0:
                    # Find all boot events
                    succ_boot_ind = np.where(
                        (self.nodes_boot_events[node][:, 0] > tm_start)
                        & (self.nodes_boot_events[node][:, 0] <= tm_end)
                    )[0]
                    if len(succ_boot_ind) > 0:
                        real_time = self.nodes_boot_events[node][succ_boot_ind][:, 0]
                        est_time = self.nodes_boot_events[node][succ_boot_ind][:, 1]
                        error = np.abs(np.mean(np.subtract(real_time, est_time)))
                        contributing_nodes += 1
                    else:
                        error = np.nan
                else:
                    error = np.nan

                nodes_error.append(error)

            nodes_error_meas_period.append(nodes_error)

            #  # If there is even one error measurement without nan value, then calculate pairwise errors
            if any(not ele for ele in np.isnan(nodes_error)):
                pairwise_err = self.calc_pairwise_errors(
                    nodes_error, contributing_nodes
                )
            else:
                pairwise_err = np.nan

            # Calculate turnout ratios
            nodes_turnout_ratios.append(
                self.calc_turnout_ratio(contributing_nodes, self.num_nodes)
            )
            pairs_turnout_ratios.append(
                self.calc_turnout_ratio(
                    comb(contributing_nodes, 2, exact=True), self.num_nodes_pairs
                )
            )
            contributing_nodes = 0
            m_lifecycle_errors.append(pairwise_err)
            nodes_error = []

        return (
            m_lifecycle_errors,
            nodes_turnout_ratios,
            pairs_turnout_ratios,
            nodes_error_meas_period,
        )

    def run_metrics_calc(self):
        """
        Run all metrics calculations
        """
        met_meas_points = self.get_met_meas_points()
        # print(f"measurment points: ", met_meas_points)
        # m_baseline_errors, nodes_turnout_ratios_mc, pairs_turnout_ratios_mc  = self.met_baseline()
        m_baseline_errors, nodes_turnout_ratios_mc, pairs_turnout_ratios_mc = [], [], []
        # m_handshake_errors, nodes_turnout_ratios_hs, pairs_turnout_ratios_hs = self.met_handshake()
        m_handshake_errors, nodes_turnout_ratios_hs, pairs_turnout_ratios_hs = (
            [],
            [],
            [],
        )
        (
            m_lifecycle_errors,
            nodes_turnout_ratios_lc,
            pairs_turnout_ratios_lc,
            nodes_error_meas_period_lc,
        ) = self.met_lifecycle()
        return (
            met_meas_points,
            m_baseline_errors,
            nodes_turnout_ratios_mc,
            pairs_turnout_ratios_mc,
            m_handshake_errors,
            nodes_turnout_ratios_hs,
            pairs_turnout_ratios_hs,
            m_lifecycle_errors,
            nodes_turnout_ratios_lc,
            pairs_turnout_ratios_lc,
            nodes_error_meas_period_lc,
        )
