from inspect import isfunction
from lure.experiment import ExperimentResult
from lure.plotter_settings.plotter_type import PlotterType
from lure.node.stats import *

import matplotlib.pyplot as plt

sleep_discharge_rate = 0.000075 * 1000
operating_discharge_rate = 0.075 * 1000
coeff = 0.2
slot_size = 5
sim_length = 172800000


class ChargingPlot(PlotterType):
    def __init__(self):
        pass

    def x_axis_vals(self, ytype=None, x_to_graph=None):
        return [x * 1000 / operating_discharge_rate for x in x_to_graph]

    def plot_upper_bounds(
        self,
        plotter=None,
        ytype=None,
        x_to_graph=None,
        experiment: ExperimentResult = None,
    ):
        bounds = []
        if ytype == "throughput":
            # plot traffic upper bound, m = 0 (horizontal), y values = max bps = traffic generation rate (pkts/ms) * ms/s *bits/pkt
            traffic_bound = []
            node0 = list(list(experiment.items())[0][1].items())[0][1][0][0]
            traffic_rate_per_node = node0.get(StatType.NODE_TRAFFIC_RATE)
            traffic_rate_system = traffic_rate_per_node * 2
            traffic_bound = [((traffic_rate_system) * 1000 * 32)] * len(x_to_graph)
            plt.plot(
                x_to_graph,
                traffic_bound,
                label="Traffic Upper Bound",
                linewidth=3,
                ls="dotted",
                zorder=0,
                color="black",
            )
            bounds.append(traffic_bound)

            # plot lifecycle ratio upper bound, m = LCR*(1pkt/time to send 1 pkt at constant power in ms)*bits/pkt, LCR = x_to_graph
            # lifecycle_bound = []
            # slot_size = 5
            # lifecycle_bound =  [float(lifecycle)*(1/slot_size)*(1000*32) for lifecycle in list(list(experiment.values())[0].keys())]
            # plt.plot(x_to_graph, lifecycle_bound, label=f'LCR Upper Bound', linewidth=3, ls='dotted', zorder=0, color='gray')
            # bounds.append(lifecycle_bound)
        elif ytype == "count":
            charging_rates = list(experiment.keys())[0].x_values
            energy_bound = [
                cr * 1000 / operating_discharge_rate * sim_length / slot_size
                for cr in charging_rates
            ]
            plt.plot(
                x_to_graph,
                energy_bound,
                label="Upper bound",
                linewidth=3,
                ls="dotted",
                zorder=0,
                color="black",
            )
            bounds.append(energy_bound)

        else:
            print(
                "Charging.upper_bound: unrecognized ytype: %s OR bad x_to_graph: %s"
                % (ytype, x_to_graph)
            )
            return

        return bounds

    def plot_charging_regions(self):
        # ----- Added for SI-----
        # sleep_discharge_rate = 0.00255 * 1000
        # operating_discharge_rate = 0.06 * 1000
        # coeff = 0.2
        plt.tight_layout()
        plt.plot(
            [sleep_discharge_rate / operating_discharge_rate] * 2,
            plt.axes().get_ylim(),
            linewidth=1.5,
            ls="solid",
            zorder=0,
            color="gray",
            label="$P_{SLEEP}$",
        )
        plt.plot(
            [
                (sleep_discharge_rate + sleep_discharge_rate * coeff * 2)
                / operating_discharge_rate
            ]
            * 2,
            plt.axes().get_ylim(),
            linewidth=1.5,
            ls="dotted",
            zorder=0,
            color="gray",
        )
        plt.plot(
            [
                (sleep_discharge_rate - sleep_discharge_rate * coeff * 2)
                / operating_discharge_rate
            ]
            * 2,
            plt.axes().get_ylim(),
            linewidth=1.5,
            ls="dotted",
            zorder=0,
            color="gray",
        )
        # plt.plot([operating_discharge_rate / operating_discharge_rate] * 2, plt.axes().get_ylim(), linewidth=1.5, ls='solid', zorder=0, color='gray')
        # plt.plot([(operating_discharge_rate + operating_discharge_rate*coeff*2) / operating_discharge_rate] * 2, plt.axes().get_ylim(), linewidth=1.5, ls='dotted', zorder=0, color='gray')
        # plt.plot([(operating_discharge_rate - operating_discharge_rate*coeff*2) / operating_discharge_rate] * 2, plt.axes().get_ylim(), linewidth=1.5, ls='dotted', zorder=0, color='gray')
        # -----------------------

    def label_plot(
        self,
        experiment=None,
        ytype=None,
        num_simulations=0,
        data_type=None,
        percentile=None,
    ):
        fontsize = 14
        if data_type == "mean":
            title_prefix = "Avg"
        elif data_type == "median":
            title_prefix = "Median"
        elif data_type == "percentile":
            title_prefix = f"{percentile} percentile"

        plt.xlabel("Charging Power Normalized to Operating Power", fontsize=fontsize)
        if ytype == "delay":
            plt.ylabel("Delay (s)", fontsize=fontsize)
            # plt.ylim(1,10000)
            # plt.title(title_prefix+' Delay '+title_suffix, fontsize=8)
        elif ytype == "active_delay":
            plt.ylabel("Active Delay (s)", fontsize=fontsize)
            # plt.ylim(0.1,10000)
            # plt.title(title_prefix+' Active Delay '+title_suffix, fontsize=8)
        elif ytype == "throughput":
            plt.ylabel("Throughput (bps)", fontsize=fontsize)

            # plt.ylim(1,10000)
            # plt.title(title_prefix+' Throughput '+title_suffix, fontsize=8)
        elif ytype == "count":
            plt.ylabel(f"{title_prefix} Packet Count", fontsize=fontsize)

        elif isfunction(ytype):
            if ytype.__name__ == "operating_times_s":
                plt.ylabel(f"{title_prefix} Operating Time (s)")
            else:
                plt.ylabel(f"{title_prefix} {ytype.__name__}", fontsize=fontsize)

        else:
            print("Charging.label_plot: unrecognized ytype: %s" % ytype)
            return
        # x_ticks = [0.01, 0.02, 0.05, 0.1, 0.15, 0.2]
        # plt.xticks(x_ticks, rotation=45)
        # plt.yscale('symlog')
        # plt.xscale('log')
        # plt.ylim(bottom=0)

    def save_plot(
        self,
        plotter=None,
        exp_index=0,
        ytype=None,
        skips_for_stabilization=0,
        data_type=None,
        percentile=None,
    ):
        if plotter is None:
            print("Charging: Need a value for plotter")
            return
        if data_type == "mean":
            title_prefix = "avg"
        elif data_type == "median":
            title_prefix = "median"
        elif data_type == "percentile":
            title_prefix = f"{percentile}percentile"

        node0 = list(list(plotter.results[exp_index].items())[0][1].items())[0][1][0][0]
        traffic_rate = node0.get(StatType.NODE_TRAFFIC_RATE)

        ystring = ytype
        if isfunction(ytype):
            ystring = ytype.__name__

        plt.tight_layout()
        plt.savefig(
            f"{plotter.save_fig_dir}{exp_index}_{title_prefix}_{ystring}_vs_charging_{traffic_rate}lambda_{skips_for_stabilization}skipped.{plotter.extension}"
        )

        # if ytype == 'delay':
        #     if skips_for_stabilization > 0:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_delay_vs_lcr_%glambda_%sskipped.%s' % (traffic_rate, skips_for_stabilization, plotter.extension))
        #     else:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_delay_vs_lcr_%glambda_allpts.%s' % (traffic_rate, plotter.extension))
        # elif ytype == 'active_delay':
        #     if skips_for_stabilization > 0:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_active_delay_vs_lcr_%glambda_%sskipped.%s' % (traffic_rate, skips_for_stabilization, plotter.extension))
        #     else:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_active_delay_vs_lcr_%glambda_allpts.%s' % (traffic_rate, plotter.extension))
        # elif ytype == 'throughput':
        #     if skips_for_stabilization > 0:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_throughput_vs_lcr_%glambda_%sskipped.%s' % (traffic_rate, skips_for_stabilization, plotter.extension))
        #     else:
        #         plt.savefig(plotter.save_fig_dir+title_prefix+'_throughput_vs_lcr_%glambda_allpts.%s' % (traffic_rate, plotter.extension))
        # else:
        #     print('Charging.save_plot: unrecognized ytype: %s' % ytype)
        #     return
