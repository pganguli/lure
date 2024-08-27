from lure.plotter_settings.plotter_type import PlotterType
from lure.node.stats import *

import matplotlib.pyplot as plt

class LambdaPlot(PlotterType):

    def __init__(self):
        xtype = 'lambda'
        pass

    def x_axis_vals(self, ytype=None, x_to_graph=None):
        if ytype == 'delay':
            x_to_graph  = [x_to_graph[i]*32*1000 for i in range(len(x_to_graph))]
        elif ytype == 'active_delay':
            x_to_graph  = [x_to_graph[i]*32*1000 for i in range(len(x_to_graph))]
        elif ytype == 'throughput':
            x_to_graph  = [x_to_graph[i]*32*1000 for i in range(len(x_to_graph))]
        else:
            print('Lambda.x_axis_vals: unrecognized ytype: %s OR bad x_to_graph: %s' % (ytype, x_to_graph))
            return
        return x_to_graph
            
    def plot_upper_bounds(self, plotter=None, ytype=None, x_to_graph=None, experiment=None):
        bounds = []
        if ytype == 'throughput':
            # plot traffic upper bound, m = 1 = maximum packets generated (bps)
            traffic_bound = [bps_per_node * 2 for bps_per_node in x_to_graph]
            #traffic_bound = [traffic_per_node*2*32*1000 for traffic_per_node in list(list(experiment.values())[0].keys())]
            plt.plot(x_to_graph, traffic_bound, label=f'Traffic U.B.', linewidth=3, ls='dotted', zorder=0, color='black')
            bounds.append(traffic_bound)
            
            # plot lifecycle ratio upper bound, m = 0 (horizontal), y values = LCR*pkts/s*bits/pkt, LCR = x_to_graph
            sim_result = list(list(experiment.series_results.values())[0].sim_results.values())[0][0]
            lcrs = []
            for n in sim_result:
                lcrs.append(n.get(StatType.NODE_LIFECYCLE_RATIO_NOMINAL))
            
            if lcrs[0]:
                min_lifecycle = min(lcrs)
                lifecycle_bound = []
                slot_size = 5
                lifecycle_bound =  [min_lifecycle*(1000 / slot_size)*32]*len(x_to_graph)
                plt.plot(x_to_graph, lifecycle_bound, label=f'LCR U.B.', linewidth=3, ls='dotted', zorder=0, color='gray')

                bounds.append(lifecycle_bound)
        else:
            print('Lambda.upper_bounds: unrecognized ytype: %s OR bad x_to_graph: %s' % (ytype, x_to_graph))
            return
        return bounds

    def label_plot(self, experiment=None, ytype=None, num_simulations=0, data_type=None, percentile=None): 
        fontsize = 16
        title_suffix = ('vs Traffic ([rx,tx]')
        if data_type is 'mean':
            title_prefix = 'Avg'
        elif data_type is 'median':
            title_prefix = 'Median'
        elif data_type is 'percentile':
            title_prefix = f'{percentile} percentile'

        if ytype == 'delay':
            plt.ylabel('Delay (s)', fontsize=fontsize)
            plt.xlabel('Per-node Traffic Rate (bps)', fontsize=fontsize)
            #plt.ylim(1,1000)
            # plt.title(title_prefix+' Delay '+title_suffix, fontsize=8)
        elif ytype == 'active_delay':
            plt.ylabel('Active Delay (s)', fontsize=fontsize)
            plt.xlabel('Per-node Traffic Rate (bps)', fontsize=fontsize)
            #plt.ylim(1,1000)
            # plt.title(title_prefix+' Active Delay '+title_suffix, fontsize=8)
        elif ytype == 'throughput':
            plt.ylabel('Median Throughput (bps)', fontsize=fontsize)
            plt.xlabel('Per-node Traffic Rate (bps)', fontsize=fontsize)
            #plt.ylim(1,1400)
            #plt.xlim(0.1, 1)
        elif ytype == 'count':
            plt.ylabel('Packets delivered', fontsize=fontsize)
            plt.xlabel('Per-node Traffic Rate (bps)', fontsize=fontsize)

        else:
            print('Lambda.label_plot: unrecognized ytype: %s' % ytype)
            return
        #x_ticks = [0.32, 3.2, 32, 320, 3200, 32000]
        #plt.xticks(x_ticks, rotation=45)
        plt.yscale('log')
        plt.xscale('log')

    def save_plot(self, plotter=None, exp_index=0, ytype=None, skips_for_stabilization=0, data_type=None, percentile=None):
        if plotter == None:
            print('Lambda: Need a value for plotter')
            return

        if data_type is 'mean':
            title_prefix = 'avg'
        elif data_type is 'median':
            title_prefix = 'median'
        elif data_type is 'percentile':
            title_prefix = f'{percentile}percentile'
        
        sim_result = list(list(plotter.results.experiment_results[exp_index].series_results.values())[0].sim_results.values())[0][0]
        for n in sim_result:
            lifecycle_ratio = n.get(StatType.NODE_LIFECYCLE_RATIO_NOMINAL)
            break
        print(lifecycle_ratio)

        plt.savefig(f'{plotter.save_fig_dir}{exp_index}_{title_prefix}_{ytype}_vs_traffic_{lifecycle_ratio}lifecycle_{skips_for_stabilization}skipped.{plotter.extension}')
        # if ytype == 'delay':
        #     if skips_for_stabilization > 0:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_delay_vs_traffic_%glifecycle_%sskipped.%s' % (lifecycle_ratio, skips_for_stabilization, plotter.extension))
        #     else:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_delay_vs_traffic_%glifecycle_allpts.%s' % (lifecycle_ratio, plotter.extension)) 
        # elif ytype == 'active_delay':
        #     if skips_for_stabilization > 0:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_active_delay_vs_traffic_%glifecycle_%sskipped.%s' % (lifecycle_ratio, skips_for_stabilization, plotter.extension))
        #     else:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_active_delay_vs_traffic_%glifecycle_allpts.%s' % (lifecycle_ratio, plotter.extension)) 
        # elif ytype == 'throughput':
        #     if skips_for_stabilization > 0:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_throughput_vs_traffic_%glifecycle_%sskipped.%s' % (lifecycle_ratio, skips_for_stabilization, plotter.extension))
        #     else:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_throughput_vs_traffic_%glifecycle_allpts.%s' % (lifecycle_ratio, plotter.extension)) 
        # elif ytype == 'count':
        #     if skips_for_stabilization > 0:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_count_vs_traffic_%glifecycle_%sskipped.%s' % (lifecycle_ratio, skips_for_stabilization, plotter.extension))
        #     else:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_count_vs_traffic_%glifecycle_allpts.%s' % (lifecycle_ratio, plotter.extension))        
        # else:
        #     print('Lambda.save_plot: unrecognized ytype: %s' % ytype)
        #     return
        
