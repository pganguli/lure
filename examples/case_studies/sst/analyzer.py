import pickle
import numpy as np
from plotter import Plotter
import os
import argparse

from lure.lure import Lure
from metrics import MetricAnalyzer
from lure.node.stats import StatType

class UtilityClass:    
    @staticmethod
    def unpickle_data(pickled_file_name):
        if(os.path.isfile(f'{pickled_file_name}') == False):
            raise OSError("File doesn't exist!")
        else:
            pickled_file = open(pickled_file_name,"rb")
            exp_data = pickle.load(pickled_file)
            pickled_file.close()
            return exp_data  
    
    @staticmethod
    def pickle_data(data, file_name):
        pickle_exp_dict = open(f"{file_name}","wb")
        pickle.dump(data, pickle_exp_dict)
        pickle_exp_dict.close()

"""
    Analyze data and generate plots
"""
class Analyzer(UtilityClass):
    def __init__(self, output_dir):
        self.sim_output_dir = output_dir
        self.lure_results = Lure.load_results(output_dir=output_dir)
        print("Lure results loaded successfully!")
        self.plotter = Plotter(f'{self.sim_output_dir}/figures')
        if not os.path.exists(f'{self.sim_output_dir}/pickled_data/'):
            os.mkdir(f'{self.sim_output_dir}/pickled_data/')
        self.initialize()

    def initialize(self):
        self.sim_time = np.round(int(np.max(self.get_sim_time())), decimals=-6)
        self.x_values, self.node_boot_events, self.nodes_die_events, self.nodes_succ_comm_events, self.nodes_time_tm10 = self.get_time_series_data()
        self.num_series = np.shape(self.node_boot_events)[0]
        self.num_trials = np.shape(self.node_boot_events)[1]
        self.num_nodes = np.shape(self.node_boot_events)[2]   
        self.met_meas_period = int(self.sim_time/20) # ms creates 20 measurement period
        self.x_values = np.array(self.x_values, dtype=float)
        print("Analyzer initialized successfully!")

    def get_sim_time(self):
        """
        The function `get_sim_time` retrieves the simulation run time from the result data.

        :return: Simulation run time, in milliseconds.
        """
        for exp_result in self.lure_results:
            for series_result in exp_result:
                for sim_results in series_result:
                    for sim_result in sim_results:
                        for s in sim_result:
                            return s.get(StatType.SIMULATION_TIME)

    def get_time_series_data(self):
        """
        The function `get_time_series_data` loads the relevant time series data from the results.
        
        :return: five arrays for the x values, the node restart events, the node die events, the node communication events, and the shared time data
        """
        restart_events = []
        die_events = []
        succ_comm_events = []
        time_tm = []
        x_values = []
        for exp_result in self.lure_results:
            for series_result in exp_result:
                for x_value, sim_results in series_result.items():
                    restart_events.append([])
                    die_events.append([])
                    succ_comm_events.append([])
                    time_tm.append([])
                    print(f'Loading time series data for {series_result.key}, xval {x_value}...')
                    x_values.append(x_value)
                    for sim_result in sim_results:
                        restart_events[-1].append([])
                        die_events[-1].append([])
                        succ_comm_events[-1].append([])
                        time_tm[-1].append([])
                        for n in sim_result:
                            restart_events[-1][-1].append(np.asarray(n.get_time_series(StatType.NODE_RESTART), dtype=object))
                            die_events[-1][-1].append(np.asarray(n.get_time_series(StatType.NODE_DIE), dtype=object))
                            succ_comm_events[-1][-1].append(np.asarray(n.get_time_series(StatType.SUCC_COMM), dtype=object))
                            time_tm[-1][-1].append(np.asarray(n.get_time_series('est_shared_time_tm'), dtype=object))
        return np.asarray(x_values, dtype=object), np.asarray(restart_events, dtype=object), np.asarray(die_events, dtype=object), np.asarray(succ_comm_events, dtype=object), np.asarray(time_tm, dtype=object)
    
    def run_metrics_analysis(self, pickle_data=False):
        """
        The `run_metrics_analysis` function performs metric analysis on a set of data and saves the results as pickled data if specified.
        
        :param pickle_data: A boolean parameter that determines whether the data should be pickled or not. If set to True, the data will be pickled, otherwise it will not be pickled, defaults to False
        (optional)
        """
        self.metric_analyzer = MetricAnalyzer()
        m_lifecycle_errors_trials = []
        nodes_turnout_ratios_lc_trials = []
        series_err_mlife = []
        series_tout_mlife = []
        m_life_errors = []
        m_life_tos = []
        for node_series in range(self.num_series):
            for trial in range(self.num_trials):
                self.metric_analyzer.init_params(self.num_nodes, self.node_boot_events[node_series, trial, :], self.nodes_die_events[node_series, trial, :], self.nodes_succ_comm_events[node_series, trial, :], self.nodes_time_tm10[node_series, trial, :], self.met_meas_period, self.sim_time)
                met_meas_points, _, _, _, _, _, _, m_lifecycle_errors, nodes_turnout_ratios_lc, _, _ = self.metric_analyzer.run_metrics_calc()
                m_lifecycle_errors_trials.append(m_lifecycle_errors)
                nodes_turnout_ratios_lc_trials.append(nodes_turnout_ratios_lc)
                # self.plotter.plot_mlife_plot(met_meas_points, m_lifecycle_errors, nodes_turnout_ratios_lc, ser=node_series, trial=trial)
                m_lifecycle_errors = []
                nodes_turnout_ratios_lc = []
            
            # Get statistics
            avg_m_lc_err = np.nanmean(m_lifecycle_errors_trials, axis=0)
            avg_m_lc_to = np.nanmean(nodes_turnout_ratios_lc_trials, axis=0)
            
            series_err_mlife.append(avg_m_lc_err)
            series_tout_mlife.append(avg_m_lc_to)
            m_life_errors.append(m_lifecycle_errors_trials)
            m_life_tos.append(nodes_turnout_ratios_lc_trials)
            m_lifecycle_errors_trials, nodes_turnout_ratios_lc_trials = [], []
            avg_m_lc_err, avg_m_lc_to = [], []
        if pickle_data:
            self.pickle_data(m_life_errors, f"{self.sim_output_dir}/pickled_data/errors_{self.sim_output_dir}")
            # print("pickle file generated successfully!")

class AggDataProcessor(UtilityClass):
    def __init__(self, out_dirs):
        self.plotter = Plotter('./')
        self.sim_out_dirs = out_dirs

    def calc_error_stats(self, ci_coeff=1.96):      
        """
        The function `calc_error_stats` calculates the median values and confidence intervals of the steady
        state errors for multiple series of data.
        
        :param ci_coeff: The `ci_coeff` parameter is a coefficient used to calculate the confidence interval (CI) for the error statistics. It is multiplied by the standard deviation of the steady state error values to determine the width of the CI. The default value is 1.96, which corresponds to a 95%
        :return: The function `calc_error_stats` returns two lists: `series_medians` and `series_cis`.
        """
        series_medians = []
        series_cis = []
        for dir in self.sim_out_dirs:
            data_error = np.array(self.unpickle_data(f"{dir}/pickled_data/errors_{dir}"))
            cis = []
            median_vals = []
            for ser in range(np.shape(data_error)[0]):
                # Take average of last 5 steady state values 
                sse_avg = np.mean(data_error[ser, :, -5:], axis=1)
                cis.append(ci_coeff * np.std(sse_avg, axis=0)/np.sqrt(np.shape(sse_avg)[0]))
                median_vals.append(np.median(sse_avg))
            series_medians.append(median_vals)
            series_cis.append(cis)
        return series_medians, series_cis
    
    def generate_plots(self, labels, x_vals, x_indices = None):
        """
        The function "generate_plots" generates plots using the provided labels and x values, along with calculated median values and confidence intervals.
        
        :param labels: The `labels` parameter is a list of labels for the x-axis of the plot
        :param x_vals: The x_vals parameter is a list of values that represent the x-axis values for the plot
        """
        median_vals, cis = self.calc_error_stats()
        if x_indices is not None:
            median_vals_tmp = []
            cis_tmp = []
            for m in median_vals:
                median_vals_tmp.append([m[i] for i in x_indices])
            for ci in cis:
                cis_tmp.append([ci[i] for i in x_indices])
            median_vals = median_vals_tmp
            cis = cis_tmp
            x_vals = [x_vals[i] for i in x_indices]
        self.plotter.plot_xseries_vs_sst(median_vals, cis, labels, x_vals)

def main():
    # Create the parser
    parser = argparse.ArgumentParser()
    # Define an argument that accepts multiple string values
    parser.add_argument('-d', '--outdirs', nargs='+', help='A list of output directories')
    parser.add_argument('-x', '--xvals', nargs='+', help='A list of lcr xvalues')
    parser.add_argument('-c', '--configs', nargs='+', help='A list of lmp configs directories')
    parser.add_argument('-p', '--plot_only', action='store_true', help='Plots from cached processed results')
    parser.add_argument('-i', '--x_indices', nargs='+', type=int, help='List of x-value indices to plot (defaults to all)')
    # Parse the arguments
    args = parser.parse_args()
    # Access the list of strings
    outdirs_list = args.outdirs
    x_vals = args.xvals
    configs = args.configs
    x_indices = args.x_indices

    if not args.plot_only:
        # iterate through all out dirs and create error pickle files 
        for outdir in outdirs_list:
            print(f"Processing out dir: {outdir}")
            analyzer = Analyzer(outdir)
            # this will create pickle files of error for each simulation
            analyzer.run_metrics_analysis(pickle_data=True)
            del analyzer
        
        print("Pickle files of all the simulations generated successfully!")

    # Process and plot pickled error files
    adp = AggDataProcessor(outdirs_list)
    adp.generate_plots(labels=configs, x_vals=x_vals, x_indices=x_indices)

if __name__ == "__main__":
    main()

    
    
