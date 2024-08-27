from inspect import isfunction
import os
import numpy as np
import seaborn
import matplotlib.pyplot as plt

from lure.results import LureResults
plt.rcParams['font.size'] = '16'
from matplotlib.widgets import Slider, Button
from lure.config.configuration import PlotterConfig
#rc('font', **{'family':'sans-serif', 'sans-serif':['FreeSans'], 'size': 18})
#rc('text', usetex=True)
from sympy import Point, Line
from typing import Hashable, List
from lure.simulation import *
from lure.config.configuration import PlotterConfig
from lure.plotter_settings.plotter_lambda import LambdaPlot
from lure.plotter_settings.plotter_lcr import LCRPlot
from lure.plotter_settings.plotter_charging import ChargingPlot
from lure.plotter_settings.plotter_capacitance import CapacitancePlot
from lure.plotter_settings.plotter_sleep_power import SleepPowerPlot
from lure.plotter_settings.plotter_lcr import LCRPlot
from lure.node.stats import StatName, StatType, StatsParser
from lure.results_parser import ResultsParser

class Plotter:
    """Contains all stardard plotters to be used with most experiment types within Lure
    """

    def __init__(self, analyzers_dict={}, trials=None, results=None, output_dir='output/figures/', extension='png', plotter_config=PlotterConfig()):
        # {'date-1':analyzer_1, 'date-2':analyzer_2, ...,}
        self.analyzers_dict = analyzers_dict
        self.trials = trials
        self.results: LureResults = results

        self.onTimes_exp_raw = []
        self.offTimes_exp_raw = []
        self.save_fig_dir = output_dir + '/'
        self.extension = extension
        os.makedirs(self.save_fig_dir, exist_ok=True)

        self.config = plotter_config

    def plot_count_vs_time(self):
        """Plots cumulative sent packets versus time
        """
        for exp_result in self.results:
            for series_key, series_result in exp_result.items():
                for x_val, sim_results in series_result.items():
                    fig, axes_list = plt.subplots(nrows=len(sim_results), sharex=True)
                    fig.set_size_inches(6, len(sim_results)*1.5)
                    trial = 0
                    for sim_result in sim_results:
                        pkt_sent_times = []
                        for node in range(len(sim_result)):
                            pkt_sent_times.append([])
                            node_data = StatsParser.get_send_events(sim_result[node])
                            for index in range(len(node_data)):
                                pkt_sent_times[node].append(node_data[index])
                        
                        xs = []
                        ys = []
                        sim_data = pkt_sent_times
                        sim_times = sim_data
                        num_sim_data = 0
                        sim_data_indices = []
                        for node in range(len(sim_data)):
                            sim_data_indices.append(0)
                            num_sim_data += len(sim_data[node])
                        
                        for i in range(num_sim_data):
                            min_time = np.inf
                            for node in range(len(sim_data)):
                                if (sim_data_indices[node] < len(sim_data[node])) and (sim_times[node][sim_data_indices[node]] < min_time):
                                    min_time = sim_times[node][sim_data_indices[node]]
                                    node_used = node
                            xs.append(sim_data[node_used][sim_data_indices[node_used]])
                            ys.append(i+1)
                            sim_data_indices[node_used] += 1
                        axes_list[trial].plot(xs, ys)
                        axes_list[trial].set_title(f'Trial {trial}', loc='left', fontdict={'fontsize': 'small'})
                        trial += 1
                    plt.xlabel('Time (ms)')
                    plt.tight_layout()
                    plt.savefig(f'{self.save_fig_dir}{series_key}_xval{x_val}.{self.extension}')
                    plt.close()

    def plot_time_series(self, names: List[StatName] = [], xval = None, time_range = (), node_ids = None, options = {}):
        """Plots a list of time series stats

        :param names: Desired names of stats to be plotted, defaults to []
        :type names: List[StatName], optional
        :param xval: The xval to retrieve a trial from, defaults to None
        :type xval: str, optional
        :param time_range: A time range to narrow the plot's x-axis to, defaults to ()
        :type time_range: tuple, optional
        :param node_ids: The node to draw stat information from, defaults to None
        :type node_ids: int, optional
        :param options: Flags for the plotting function. Includes 'discrete' currently, defaults to {}
        :type options: dict, optional
        """
        linestyles = ['solid', 'dashed', 'dotted']
        for exp_result in self.results:
            for series_key, series_result in exp_result.items():
                for sim_result in series_result.sim_results[xval]:
                    with sim_result as t:
                        if node_ids:
                            stats_list = [t.results[i] for i in node_ids]
                        else:
                            stats_list = t.results
                    if len(linestyles) < len(stats_list):
                        stats_list = stats_list[:len(linestyles)]

                    if names:
                        ts_names = names
                    else:
                        ts_names = stats_list[0].time_series_dict.keys()

                    fig, axes_list = plt.subplots(nrows=len(ts_names), sharex=True)
                    if not isinstance(axes_list, np.ndarray):
                        axes_list = [axes_list]
                    fig.set_size_inches(6, len(ts_names)*1.75)

                    for node_index, s in enumerate(stats_list):
                        node_id = s.get(StatType.NODE_ID)
                        
                        for i, name in enumerate(ts_names):
                            xs, ys = s.get_time_series_x_y(name)

                            try:
                                try:
                                    discrete = options[name]['discrete']
                                except:
                                    discrete = False
                                
                                if discrete:
                                    new_ys = [ys[0]]
                                    new_xs = [xs[0]]
                                    for j, (x, y) in enumerate(zip(xs[1:], ys[1:])):
                                        new_ys.extend([ys[j], y])
                                        new_xs.extend([x, x])
                                    xs = new_xs
                                    ys = new_ys
                                    if time_range and xs[-1] < time_range[1]:
                                        xs.append(time_range[1])
                                        ys.append(ys[-1])
                                elif isinstance(ys[0], bool):
                                    new_ys = []
                                    new_xs = []
                                    for x, y in zip(xs, ys):
                                        new_ys.extend([not y, y])
                                        new_xs.extend([x, x])
                                    xs = new_xs
                                    ys = new_ys
                                    axes_list[i].set_yticks([0, 1])
                                    axes_list[i].set_yticklabels(['False', 'True'])
                                elif isinstance(ys[0], Enum):
                                    members = ys[0].__class__.__members__
                                    values = list(members.values())
                                    ys = [values.index(y) for y in ys]
                                    new_ys = [ys[0]]
                                    new_xs = [xs[0]]
                                    for j, (x, y) in enumerate(zip(xs[1:], ys[1:])):
                                        new_ys.extend([ys[j], y])
                                        new_xs.extend([x, x])
                                    xs = new_xs
                                    ys = new_ys
                                    axes_list[i].set_yticks(range(len(values)))
                                    axes_list[i].set_yticklabels([v.value for v in values])
                            except:
                                xs = []
                                ys = []

                            axes_list[i].plot(xs, ys, ls=linestyles[node_index], label=f'Node {node_id}')
                            axes_list[i].set_title(str(name).replace('_', '-'), loc='left', fontdict={'fontsize': 'medium'})
                            if time_range:
                                axes_list[i].set_xlim(time_range)
                    axes_list[0].legend(bbox_to_anchor=(0.5, 1.35), loc='lower center', ncol=2, fancybox=True, shadow=False, edgecolor='black')
                    plt.xlabel('Time (ms)')
                    #axes_list[0].set_title(f'Node {s.get(StatType.NODE_ID)}')
                    plt.tight_layout()
                    plt.savefig(f'{self.save_fig_dir}/time_series_{series_key}_x{xval}_nids{node_ids}_seed{sim_result.seed}_timerange{time_range}.{self.extension}')
                    plt.close()

    def plot_stat_distributions(self, stat_name: StatName, xval: Hashable = None, postfix: str = ""):
        """Plots distributions of time series stats from a simulation

        :param stat_name: The name of the desired stat
        :type stat_name: StatName
        :param xval: Xvalue of the desired simulation, defaults to None
        :type xval: Hashable, optional
        :param postfix: Appended to the file name, defaults to ""
        :type postfix: str, optional
        """
        for exp_result in self.results:
            for series_key, series_results in exp_result.items():
                vals = []
                for sim_result in series_results.sim_results[xval]:
                    for s in sim_result:
                        ts, vs = s.get_time_series_x_y(stat_name)
                        if vs:
                            vals.extend(vs)
                        else:
                            vals.append(s.get(stat_name))
                plt.hist(vals)
                plt.savefig(f"{self.save_fig_dir}/{stat_name}_{series_key}_{postfix.replace('.', '-')}.pdf")
                plt.close()

    def plot_stat_list_distribution(self, stat_name: StatName, xval: Hashable = None):
        """Plots the distribution of a stat list

        :param stat_name: Name of the desired plotting stat
        :type stat_name: StatName
        :param xval: Desired XValue to be plotted, defaults to None
        :type xval: Hashable, optional
        """
        for exp_result in self.results:
            for series_key, series_result in exp_result.items():
                for sim_result in series_result.sim_results[xval]:
                    for s in sim_result:
                        vals = s.get_list(stat_name)
                        if vals:
                            plt.hist(vals, density=True)
                            if stat_name is StatType.PACKET_ARRIVAL_INTERVALS:
                                rate = s.get(StatType.NODE_TRAFFIC_RATE)
                                if rate:
                                    print(f'Traffic rate is {rate}.')
                                    from scipy.stats import expon
                                    x = np.linspace(min(vals), max(vals), 100)
                                    plt.plot(x, expon.pdf(x, scale=1/rate), label='expon pdf')
                                else:
                                    print(f'Trying to plot ideal distribution but no traffic rate found.')
                            plt.savefig(f"{self.save_fig_dir}/{stat_name}_{series_key}_n{s.get(StatType.NODE_ID)}.{self.extension}")
                            plt.close()

    def plot_y_vs_x(self, xtype=None, ytype=None, data_type='mean', xth_percentile=0, show_ci=False, ci_percent=95, skips_for_stabilization=0, legend_placement = 'upper right'):
        """Plots a ytype plot (throughput, delay) versus an xtype (charging, traffic rate)

        :param xtype: lambda, charging, sleep_power, capacitance, defaults to None
        :type xtype: _type_, optional
        :param ytype: delay, active_delay, throughput, count, all, defaults to None
        :type ytype: _type_, optional
        :param data_type: mean, median, or precentile, defaults to 'mean'
        :type data_type: str, optional
        :param xth_percentile: Specifies a percentile for the percentile data_type, defaults to 0
        :type xth_percentile: int, optional
        :param show_ci: Plot confidence intervals, defaults to False
        :type show_ci: bool, optional
        :param ci_percent: Confidence interval percentage, defaults to 95
        :type ci_percent: int, optional
        :param skips_for_stabilization: How many packets should be skipped at the beginning of a simulation to stabilize its results, defaults to 0
        :type skips_for_stabilization: int, optional
        :param legend_placement: Placement of the legend on the plot, defaults to 'upper right'
        :type legend_placement: str, optional
        """
        #Verify ci_percent
        ci_percentages = [95, 98, 99]
        if ci_percent not in ci_percentages:
            print('Plotter: ci percentages must be 95, 98, or 99')
            return

        #Verify data_type
        data_types = ['mean', 'median', 'percentile']
        if data_type not in data_types:
            print('Plotter: unrecognized ytype: %s' % ytype)
            return
        elif (data_types is 'percentile') and (xth_percentile < 1 or xth_percentile > 99):
            print('Plotter: percentile plots must specify the percentile in the xth_percentile parameter') 
            return
        
        #Verify ytype
        ytypes = ['delay', 'active_delay', 'throughput', 'count', 'all']
        if ytype not in ytypes:
            print('Plotter: unrecognized ytype: %s' % ytype)
            return

        # #Verify experiment
        # if not self.experiment:
        #     return

        #Verify xtype
        if xtype == 'lambda':
            plotter_type = LambdaPlot()
        elif xtype == 'lcr':
            plotter_type = LCRPlot()
        elif xtype == 'charging':
            plotter_type = ChargingPlot()
        elif xtype == 'lcr':
            plotter_type = LCRPlot()
        elif xtype == 'sleep_power':
            plotter_type = SleepPowerPlot()
        elif xtype == 'capacitance':
            plotter_type = CapacitancePlot()
        else:
            plotter_type = None
            print('Plotter: unrecognized xtype: %s' % xtype)
            return

        if ytype == 'all':
            num_plots = len(ytypes) - 1
        else:
            num_plots = 1

        # print(self.config.xlabel) #Debug

        # loop through each type of graph: delay, throughput
        for plot_index in range(0,num_plots):
            for exp_index, exp_result in enumerate(self.results):
                plotted_bounds = 0
                final_vals = {}
                num_simulations = self.trials
                # loop through each series (line on graph)
                for series_key, series_config in self.config.series.items():
                    try:
                        series_result = exp_result.series_results[series_key]
                    except IndexError:
                        print(f'Series key {series_key} not found in data.')
                        continue

                    x_to_graph = []
                    y_to_graph = []
                    shading_values = []

                    # loop through each i_var, a loop is an x value on plot
                    for x_val, sim_results in series_result.items():
            
                        y_datapoints = []
                        # loop through n simulations
                        for sim_result in sim_results:

                            if (ytype == 'delay' or ytype == 'active_delay') or (ytype == 'all' and (ytypes[plot_index] == 'delay' or ytypes[plot_index] == 'active_delay')):
                                # get_delay returns an array [delay, time of sent pkt], each delay time represents the time between when a pkt entered the queue and when it was sent successfully                                
                                if ytype == 'active_delay' or (ytype == 'all' and ytypes[plot_index] == 'active_delay'):
                                    active = True
                                else:
                                    active = False

                                delays = []
                                pkt_sent_times = []
                                for node, s in enumerate(sim_result):
                                    delays.append([])
                                    pkt_sent_times.append([])
                                    if active: # Determine action based off of delay type
                                        node_data = StatsParser.single_hop_active_delays(s)
                                    else:
                                        node_data = StatsParser.single_hop_delays(s)
                                    for index in range(len(node_data)):
                                        delays[node].append(node_data[index][0])
                                        pkt_sent_times[node].append(node_data[index][1])

                                # combine delays
                                combined_delays = StatsParser.combine_node_data(sim_data=delays, sim_times=pkt_sent_times)

                                # use subset of data at stabilization point
                                if skips_for_stabilization > 0:
                                    combined_delays = combined_delays[skips_for_stabilization:len(combined_delays)]

                                # add combined_delays to y_datapoints
                                for index in range(len(combined_delays)):
                                    y_datapoints.append(combined_delays[index])
                                    
                            elif ytype == 'throughput' or (ytype == 'all' and ytypes[plot_index] == 'throughput'):
                                if skips_for_stabilization == 0:
                                    throughput = StatsParser.total_throughput_bps(sim_result)
                                else:
                                    throughput = StatsParser.total_steady_throughput_bps(sim_result, skips_for_stabilization)
                                # calculate throughput and add to y_datapoints
                                #throughput = throughput / 32.0
                                y_datapoints.append(throughput)

                            elif ytype == 'count' or (ytype == 'all' and ytypes[plot_index] == 'count'):
                                counts = []
                                for s in sim_result:
                                    count = s.get(StatType.PACKETS_SENT_APP)
                                    if count is None:
                                        counts.append(0)
                                    else:
                                        counts.append(count)
                                y_datapoints.append(sum(counts))

                            elif isfunction(ytype):
                                y_datapoints.extend(ytype(sim_result))
                                
                            else:
                                ##This should never happen because we filter these out at the beginning
                                pass

                            # end of current simulation
                        # end of all simulations
                        
                        # average the the points across each simulation (n averaged together per x value)
                        # loop through each value (either one throughput per simulation or one delay per packet per simulation)
                        if data_type == 'mean':
                            y_sum = 0
                            for i in range(len(y_datapoints)):
                                y_sum = y_datapoints[i] + y_sum

                        # confidence interval (confidence coefficient 1.96 = 95% confidence, 2.33 = 98%, 2.58 = 99%)
                        if ci_percent == 95:
                            ci_coefficient = 1.96
                        elif ci_percent == 98:
                            ci_coefficient = 2.33
                        elif ci_percent == 99:
                            ci_coefficient = 2.58
                        ci = ci_coefficient * np.std(y_datapoints)/np.sqrt(len(y_datapoints))   

                        if(show_ci):
                            shading_value = ci
                        else: 
                            shading_value = 0

                        # divide each sum by the number of simulations
                        if len(y_datapoints) == 0:
                            y_to_graph.append(0)
                        else:
                            # plot the average of y datapoints
                            if data_type == 'mean':
                                y_to_graph.append(y_sum/len(y_datapoints))
                            elif data_type == 'median':
                                y_to_graph.append(np.median(y_datapoints))
                            # plot 95th percentil
                            elif data_type == 'percentile': 
                                y_to_graph.append(np.percentile(y_datapoints, xth_percentile))

                        x_to_graph.append(x_val)
                        shading_values.append(shading_value)
                        # end of adding point

                    plot_legend_labels = [series_result.key]

                    # Potentially reassign x values depending on plotting type
                    x_to_graph = plotter_type.x_axis_vals(ytype, x_to_graph)

                    # plot a single line on plot
                    if ytype == 'delay' or (ytype == 'all' and ytypes[plot_index] == 'delay'):
                        y_to_graph  = [y_to_graph[i]/1000 for i in range(len(y_to_graph))] # convert from ms to s
                    elif ytype == 'active_delay' or (ytype == 'all' and ytypes[plot_index] == 'active_delay'):
                        y_to_graph  = [y_to_graph[i]/1000 for i in range(len(y_to_graph))]  # convert from ms to s
                    elif ytype == 'throughput' or (ytype == 'all' and ytypes[plot_index] == 'throughput'):
                        y_to_graph  = [y_to_graph[i] for i in range(len(y_to_graph))] # convert from pkts/ms to bps, 1 pkt = 32bit payload
                    else:
                        #This should never happen because we filter these out at the beginning
                        pass

                    final_vals[series_result.key] = y_to_graph
                    
                    print(x_to_graph)
                    print(y_to_graph)
                    print('------------')
                    plt.plot(x_to_graph, y_to_graph, zorder=2, **series_config)
                    if show_ci:
                        if (ytype == 'delay' or ytype == 'active_delay') or (ytype == 'all' and (ytypes[plot_index] == 'delay' or ytypes[plot_index] == 'active_delay')):
                            shading_values = [shading_values[i]/1000 for i in range(len(y_to_graph))] # convert from ms to s
                        elif ytype == 'throughput' or (ytype == 'all' and ytypes[plot_index] == 'throughput'):
                            shading_values = [shading_values[i] for i in range(len(y_to_graph))] # convert from pkts/ms to bps, 1 pkt = 32bit payload
                        else:
                            #This should never happen because we filter these out at the beginning
                            pass
                    y_lower_to_graph = [max((y_to_graph[y_index]-shading_values[y_index]),0) for y_index in range(len(y_to_graph))]
                    y_upper_to_graph = [max((y_to_graph[y_index]+shading_values[y_index]),0) for y_index in range(len(y_to_graph))]
                    try:
                        plt.fill_between(x_to_graph, y_lower_to_graph, y_upper_to_graph, alpha=.15, color=series_config["color"], lw=0, zorder=1)
                    except KeyError:
                        plt.fill_between(x_to_graph, y_lower_to_graph, y_upper_to_graph, alpha=.15, lw=0, zorder=1)

                    # end of plotting current lmp config
                # end of plotting all points
                if plotted_bounds == 0:
                    # plot upper bounds for throughput plot, not needed for normalized throughput
                    plot_upper_bound = self.config.plot_upper_bounds # 0 = don't plot, 1 = plot
                    if plot_upper_bound == 1:
                        bounds = plotter_type.plot_upper_bounds(self, ytype, x_to_graph, exp_result)
                    # plot vertical line at intersection of traffic and lifecycle upper bounds
                    plot_intersection_bool = self.config.plot_bound_intersection_vert # 0 = don't plot, 1 = plot
                    if plot_intersection_bool == 1 and bounds is not None:
                        self.plot_vert_intersection(bounds[0], bounds[1], x_to_graph)
                    plotted_bounds = 1

                if xtype == 'charging':
                    plotter_type.plot_charging_regions()

                # set xtype and ytype lables and format axes
                plotter_type.label_plot(exp_result, ytype, num_simulations, data_type=data_type, percentile=xth_percentile)
                fontsize = 16
                plt.yticks(fontsize=fontsize)
                plt.xticks(fontsize=fontsize)

                plt.legend(fontsize=(fontsize-2), loc=legend_placement)
                # draggable would be nice for an interactive mode
                plt.tight_layout()
                
                plotter_type.save_plot(self, exp_index, ytype, skips_for_stabilization, data_type=data_type, percentile=xth_percentile)

                plt.close() 

                print(f'Final values for {ytype}:')
                for k, v in final_vals.items():
                    print(f'\tRaw - {k}: {v}')
                    try:
                        baseline_vals = final_vals[self.config.config['baseline']]
                        normalized_vals = np.divide(v, baseline_vals)
                        print(f'\tNormalized to {self.config.config["baseline"]} - {k}: {normalized_vals}')
                    except KeyError:
                        print('No baseline for normalization found. Configure key "baseline" in plot.json.')

    def plot_time_series_interactive(self, names: List[StatName] = [], exp_index=0, series_index=None, series_metadatakey=None, xval=None, trial_index=0, node_ids = None, options = {}):
        linestyles = ['solid', 'dashed', 'dotted']
        colors = ['r', 'g', 'b', 'c', 'm', 'y']
        # for exp_result in self.results:
        #     for series_result in ResultsParser.getSeriesResultByIndex exp_result.items():
        #         for seed, sim_result in enumerate(series_result[xval]):
        exp_result = ResultsParser.getExperiment(self.results, exp_index)
        if series_index != None:
            series_result = ResultsParser.getSeriesResultByIndex(exp_result, series_index)
        elif series_metadatakey != None:
            series_result = ResultsParser.getSeriesResultByMetadataKey(exp_result, series_metadatakey)
        else:
            raise Exception("Provide either series_index or series_metadatakey")
        sim_result = ResultsParser.getTrial(series_result, xval, trial_index)
        with sim_result as t:
            if node_ids:
                stats_list = [t.results[i] for i in node_ids]
            else:
                stats_list = t.results
        if (len(colors)) < len(stats_list):
            raise Exception('WARNING: Not enought unique line colors, aborting...')
        if names:
            ts_names = names
        else:
            ts_names = stats_list[0].time_series_dict.keys()

        fig, axes_list = plt.subplots(nrows=len(ts_names), sharex=True)
        fig.set_size_inches(7, (len(ts_names)+1)*1.5)
        plt.subplots_adjust(bottom=0.2,
                            right=0.8,
                            hspace=0.3)
        try:
            temp = axes_list[0]
        except:
            axes_list = [axes_list]

        for node_index, s in enumerate(stats_list):
            node_id = s.get(StatType.NODE_ID)
            
            for i, name in enumerate(ts_names):
                xs, ys = s.get_time_series_x_y(name)

                try:
                    try:
                        discrete = options[name]['discrete']
                    except:
                        discrete = False
                    
                    if discrete:
                        new_ys = [ys[0]]
                        new_xs = [xs[0]]
                        for j, (x, y) in enumerate(zip(xs[1:], ys[1:])):
                            new_ys.extend([ys[j], y])
                            new_xs.extend([x, x])
                        xs = new_xs
                        ys = new_ys
                    elif isinstance(ys[0], bool):
                        new_ys = []
                        new_xs = []
                        for x, y in zip(xs, ys):
                            new_ys.extend([not y, y])
                            new_xs.extend([x, x])
                        xs = new_xs
                        ys = new_ys
                        axes_list[i].set_yticks([0, 1])
                        axes_list[i].set_yticklabels(['False', 'True'])
                    elif isinstance(ys[0], Enum):
                        members = ys[0].__class__.__members__
                        values = list(members.values())
                        ys = [values.index(y) for y in ys]
                        new_ys = [ys[0]]
                        new_xs = [xs[0]]
                        for j, (x, y) in enumerate(zip(xs[1:], ys[1:])):
                            new_ys.extend([ys[j], y])
                            new_xs.extend([x, x])
                        xs = new_xs
                        ys = new_ys
                        axes_list[i].set_yticks(range(len(values)))
                        axes_list[i].set_yticklabels([v.value for v in values])
                except:
                    xs = []
                    ys = []
                axes_list[i].plot(xs, ys, ls=linestyles[node_index%(len(linestyles))], color=colors[node_index%(len(colors))], label=f'Node {node_id}')
                axes_list[i].set_title(str(name).replace('_', '-'), loc='left', fontdict={'fontsize': 'medium'})
        k = 0
        num_handles_labels = 0    
        while(num_handles_labels < len(node_ids)-1):
            handles, labels = axes_list[k].get_legend_handles_labels()
            num_handles_labels += len(labels)
            k += 1
        axes_list[0].legend(handles, labels, loc='upper left', bbox_to_anchor=(1,1), ncol=1, labelspacing=0.75, fancybox=True, shadow=True)
        plt.xlabel('Time (ms)')
        xmin, xmax, ymin, ymax = axes_list[0].axis() #+10
        end_time = xmax
        ax_time = fig.add_axes([0.2, 0.1, 0.65, 0.03])
        stime = Slider(
            ax_time, "Time (ms)", 0, end_time, 
            valstep=10,
            color="green"
        )
        def update(val):
            ax = axes_list[0]
            pos = stime.val
            xmin, xmax, ymin, ymax = ax.axis() #+10
            ax_width = xmax-xmin
            if(ax_width > 1000):
                ax_width = 100
            ax.axis([pos, pos+ax_width, ymin, ymax]) #+10
            fig.canvas.draw_idle()
        
        ax_b1 = fig.add_axes([0.225, 0.025, 0.1, 0.04])
        ax_b2 = fig.add_axes([0.375, 0.025, 0.1, 0.04])
        button_dec_range = Button(ax_b1, ' - Range', hovercolor='0.975')
        button_inc_range = Button(ax_b2, ' + Range', hovercolor='0.975')
        ax_b3 = fig.add_axes([0.525, 0.025, 0.1, 0.04])
        ax_b4 = fig.add_axes([0.675, 0.025, 0.1, 0.04])
        button_shift_left = Button(ax_b3, ' Left ', hovercolor='0.975')
        button_shift_right = Button(ax_b4, ' Right ', hovercolor='0.975')
        ax_b5 = fig.add_axes([0.85, 0.955, 0.1, 0.04])
        button_save = Button(ax_b5, 'Save', hovercolor='0.975')
        

        def increase_range(val):
            ax = axes_list[0]
            increase_val = 20
            xmin, xmax, ymin, ymax = ax.axis()
            ax.axis([xmin, xmax+increase_val, ymin, ymax]) #+10
            fig.canvas.draw_idle()
        
        def decrease_range(val):
            ax = axes_list[0]
            decrease_val = 20
            xmin, xmax, ymin, ymax = ax.axis()
            if xmax - xmin > decrease_val:
                ax.axis([xmin, xmax-decrease_val, ymin, ymax]) #+10
            else:
                print("WARNING: Cannot decrease range anymore")
            fig.canvas.draw_idle()

        def shift_left(val):
            ax = axes_list[0]
            shift_val = 10
            xmin, xmax, ymin, ymax = ax.axis() #+10
            ax.axis([xmin-shift_val, xmax-shift_val, ymin, ymax]) #+10
            fig.canvas.draw_idle()

        def shift_right(val):
            ax = axes_list[0]
            shift_val = 10
            xmin, xmax, ymin, ymax = ax.axis() #+10
            ax.axis([xmin+shift_val, xmax+shift_val, ymin, ymax]) #+10
            fig.canvas.draw_idle()
        
        def save_plot(val):
            ax = axes_list[0]
            xmin, xmax, ymin, ymax = ax.axis() #+10
            self.plot_time_series(names=names, xval = xval, time_range = (xmin, xmax), node_ids = node_ids, options = options)
        
        stime.on_changed(update)
        button_inc_range.on_clicked(increase_range)
        button_dec_range.on_clicked(decrease_range)
        button_shift_left.on_clicked(shift_left)
        button_shift_right.on_clicked(shift_right)
        button_save.on_clicked(save_plot)
    
        plt.show()    

    #Used to plot intersection between bounds
    def plot_vert_intersection(self, line1_ys, line2_ys, xs):
        """Plots a vertical line at the intersection of two lines

        :param line1_ys: First line's y values
        :type line1_ys: _type_
        :param line2_ys: Second line's y values
        :type line2_ys: _type_
        :param xs: X values shared by both lines
        :type xs: _type_
        """
        first_x = xs[0]
        last_x = xs[len(xs)-1]

        first_y_line1 = line1_ys[0]
        last_y_line1 = line1_ys[len(line1_ys)-1]

        first_y_line2 = line2_ys[0]
        last_y_line2 = line2_ys[len(line2_ys)-1]

        line1_start = Point(first_x, first_y_line1)
        line1_end = Point(last_x, last_y_line1)
        try:
            line1 = Line(line1_start, line1_end)
        except ValueError:
            return

        line2_start = Point(first_x, first_y_line2) 
        line2_end = Point(last_x, last_y_line2)
        line2 = Line(line2_start, line2_end)

        intersection_pt = line1.intersection(line2)
        x_intersection_pt = float(intersection_pt[0][0])
        
        if(x_intersection_pt > 0) and (x_intersection_pt <= float(xs[len(xs)-1])):
            y_for_vert = []
            y_for_vert.append(0)
            y_for_vert.append(line1_ys[len(line1_ys)-1])  # line1_ys is likely the max y value on the graph
            x_for_vert = [x_intersection_pt]*len(y_for_vert)
            plt.plot(x_for_vert, y_for_vert, label=f'Intersection', linestyle = 'dotted', color='black')

    # TODO: confirm this works as expected, update function name
    def plot_vs_x_y(self, postfix, xtype='extratime', ytype='extratime', ztype='delay', normalize_to=None, quantile=None, xscale='linear', surface3d=True):
        ztypes = ['delay', 'throughput', 'lifecycle']
        if ztype not in ztypes:
            self.debug(f'Plotter: unrecognized ytype: {ytype}')
            return

        ytypes = ['extratime']
        if ytype not in ytypes:
            self.debug('Plotter: ytype not implemented yet')
            return

        if not self.results or len(self.results.experiment_results) <= 1:
            self.debug('Plotter: plot_vs_x_y: Not enough dimensions - did you mean to use plot_vs_x instead?')
            return

        xs = list(self.results.experiment_results[0].series_results.values())[0].x_values
        ys = xs
        # if ytype == 'extratime':
        #     ys = [e.extra_comm_times[0] for e in self.experiment]
        # else:
        #     self.debug('No ys')

        #a z is a value for a given x from a given experiment (i.e. given y)

        series = list(self.results.experiment_results[0].series_results.keys())
        zs = {x: {} for x in xs}
        i =0
        for x in xs:
            zs[x] = {y: {} for y in ys}
            for y in ys:
                zs[x][y] = {p: [] for p in series}
                i+=1

        for e, y in zip(self.results, ys):
            #y = e.extra_comm_times[0]
            for p in series:
                for x in xs:
                    series_result = e.series_results[p]
                    stat_sets = series_result.sim_results[x]
                    for stats_list in stat_sets:
                        if ztype == 'delay':
                            zs[x][y][p].extend(np.divide([t[0] for t in StatsParser.time_to_handshakes([stats_list[0]])], 1000.0))
                            #zs[x][y][p].append(e.sim_time / 1000.0 / nodes[0].get_num_successful_comms())
                        elif ztype == 'throughput':
                            zs[x][y][p].append(StatsParser.total_throughput_bps(stats_list))
                        elif ztype == 'lifecycle':
                            zs[x][y][p].append(stats_list[0].get(StatType.NODE_LIFECYCLE_RATIO))

        if ztype == 'delay':
            cmap = 'viridis_r'
        else:
            cmap = 'viridis'

        X = np.divide(xs, 5) 
        Y = np.divide(ys, 5)
        Z = np.array([[np.median(zs[x][y][series[0]]) for x in xs] for y in ys])
        
        fig = plt.figure()

        if surface3d:
            X, Y = np.meshgrid(X, Y)
            ax = fig.add_subplot(projection='3d')

            surface = ax.plot_surface(X, Y, Z, cmap=cmap)
            plt.colorbar(surface)
        else:
            Z = np.round(Z, decimals=2)

            #plt.contour(X, Y, Z, 40, cmap=cmap)
            fig, ax = plt.subplots(figsize = (10, 7))
            im = ax.imshow(Z, cmap=cmap)
            
            plt.gca().invert_yaxis()
            plt.colorbar(im)            
            

            # We want to show all ticks...
            ax.set_xticks(np.arange(len(X)))
            ax.set_yticks(np.arange(len(Y)))
            # ... and label them with the respective list entries
            ax.set_xticklabels(X)
            ax.set_yticklabels(Y)
            ax.set_xlabel("Rx LMP Config", fontsize=15)
            ax.set_ylabel("Tx LMP Config", fontsize=15)
            
            # Rotate the tick labels and set their alignment.
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
                    rotation_mode="anchor", fontsize=20)
            plt.setp(ax.get_yticklabels(), ha="right",
                    rotation_mode="anchor", fontsize=20)
            
            # Loop over data dimensions and create text annotations.
            for i in range(len(Y)):
                for j in range(len(X)):
                    text = ax.text(j, i, Z[i, j],
                                ha="center", va="center", color="w")

        if xtype == 'distance':
            plt.xlabel('Distance of Node B from PTX (m)')
        elif xtype == 'fdo':
            plt.xlabel('Fast-die ontime (ms)')
        elif xtype == 'clkerr':
            plt.xlabel('Exp. mag. of relative clock error')
        elif xtype == 'esterr':
            plt.xlabel('Max relative offtime estimation error')
        elif xtype == 'buftime':
            plt.xscale('log')
            plt.xlabel('Safety margin parameter $\\beta$')
        elif xtype == 'extratime':
            #plt.xscale('log')
            plt.xlabel('LMP configuration (node 1 - sender)')
            plt.ylabel('LMP configuration (node 0 - receiver)')
        elif xtype == 'bootup':
            plt.xlabel('Node boot time (ms)')


        if ztype == 'delay':
            plt.title('Median TTH (s)')
        elif ztype == 'throughput':
            plt.title('Median throughput (bps)')


        # plt.title(postfix)

        # plt.ylim((0, 1000))

        # plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left', ncol=2, mode="expand", borderaxespad=0.)



        plt.savefig(self.save_fig_dir + 'avg_%s_vs_%s_%s_3d.%s' % (ztype, xtype, postfix.replace('.', '-'), self.extension))
        plt.close()


    def plot_cdf(self, xtype: str = 'delay', xval: Hashable = None, skips_for_stabilization: int = 0, legend_placement: str = 'best'):
        """Plot cumulative distribution function

        :param xtype: Only 'delay' is available, defaults to 'delay'
        :type xtype: str, optional
        :param xval: Desired XValue to plot, defaults to None
        :type xval: Hashable, optional
        :param skips_for_stabilization: Packets to be skipped to stabilize results, defaults to 0
        :type skips_for_stabilization: int, optional
        :param legend_placement: Where to place the legend on the plot, defaults to 'best'
        :type legend_placement: str, optional
        :raises ValueError: Raises if xtype is not found in the supported list
        """
        xtypes = ['delay']
        if xtype not in xtypes:
            raise ValueError(f'xtype {xtype} not found in supported list {xtypes}')

        for exp_index, exp_result in enumerate(self.results):
            for series_metadata, series_result in exp_result.items():
                try:
                    series_config = self.config.series[series_metadata.key]
                except KeyError:
                    continue
                sim_results = series_result[xval]

                # values will be a flat list of all values from all nodes from all trials for the given xval
                values = []
                for sim_result in sim_results:
                    for stats in sim_result:
                        if xtype == 'delay':
                            num_generated = stats.get(StatType.PACKETS_GENERATED)
                            delays = []
                            try:
                                delays, _ = zip(*StatsParser.single_hop_delays(stats))
                                values.extend(np.divide(delays, 1000))
                            except ValueError:
                                print(f'Zero packets for a node in series {series_metadata.key} at {xval}')
                            plt.xlabel('Delay (s)')

                # We have the values, now plot them for this series...
                seaborn.ecdfplot(values, label=series_config['label'], color=series_config['color'], ls=series_config['ls'])

            plt.yticks(fontsize=11)
            plt.xticks(fontsize=11)
            plt.ylabel('CDF', fontsize=11)
            plt.legend(fontsize=11, loc=legend_placement)
            plt.xlim(0, 1400)
            plt.savefig(f'{self.save_fig_dir}/{xtype}_{xval}_cdf_{exp_index}.{self.extension}')
            plt.close()
