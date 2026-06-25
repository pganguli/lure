import os
from typing import List, Tuple
from matplotlib import rc

rc("font", **{"family": "sans-serif", "sans-serif": ["FreeSans"], "size": 18})
rc("text", usetex=True)
import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rcParams.update(mpl.rcParamsDefault)
from lure.simulation import *
from lure.lure import LureResults
from lure.results_parser import ResultsParser
from lure.node.stats import *
from matplotlib.widgets import Slider, Button


class PlotterSpecial:
    """
    This is a class that can be added and removed from src/lure to plot specialized/specific trends. It's primary use will be for simulation papers.
    It was created to avoid cluttering the core plotter of LURE.

    Args:
        analyzers_dict: A dictionary of analyzers. Each is a date and each value is a expAnalyzer object. (defined in "exp_data_analyzer.py")
        trials: ...

    """

    def __init__(
        self, analyzers_dict={}, trials=None, results=None, dir="output/figures/"
    ):
        # {'date-1':analyzer_1, 'date-2':analyzer_2, ...,}
        self.analyzers_dict = analyzers_dict
        self.trials = trials
        self.results: LureResults = results

        self.onTimes_exp_raw = []
        self.offTimes_exp_raw = []
        self.save_fig_dir = dir + "/"
        os.makedirs(self.save_fig_dir, exist_ok=True)

    def plot_time_series(self, names: List[StatName] = [], time_range=(), system=None):
        for node in system:
            if names:
                ts_names = names
            else:
                ts_names = node.time_series_dict.keys()
            fig, axes_list = plt.subplots(nrows=len(ts_names), sharex=True)
            fig.set_size_inches(6, len(ts_names) * 1.5)
            for i, name in enumerate(ts_names):
                xs, ys = node.get_time_series_x_y(name)
                if time_range:
                    try:
                        xs, ys = zip(
                            *[
                                (x, y)
                                for x, y in zip(xs, ys)
                                if x >= time_range[0] and x <= time_range[1]
                            ]
                        )
                    except ValueError:
                        xs = []
                        ys = []
                try:
                    if isinstance(ys[0], bool):
                        new_ys = []
                        new_xs = []
                        for x, y in zip(xs, ys):
                            new_ys.extend([not y, y])
                            new_xs.extend([x, x])
                        xs = new_xs
                        ys = new_ys
                except IndexError:
                    pass
                axes_list[i].plot(xs, ys)
                axes_list[i].set_title(
                    str(name).replace("_", "\_"),
                    loc="left",
                    fontdict={"fontsize": "small"},
                )
            plt.xlabel("Time (ms)")
            plt.tight_layout()
            plt.savefig(f"{self.save_fig_dir}/mac_{node.get(StatType.NODE_ID)}.pdf")
            plt.close()

    def plot_macstates_vs_time(self, system=None, time_range: Tuple = None):
        """
        Creates a mac_state vs time plot that can be interacted with
        """
        ts_names = [
            StatType.MAC_IS_SENDING,
            StatType.MAC_IS_TRANSMITTING,
            StatType.MAC_IS_LISTENING,
            StatType.MAC_IS_RECEIVING,
        ]
        short_names = ["Sending", "Transmitting", "Listening", "Receiving"]
        fig, axs = plt.subplots(nrows=len(ts_names), sharex=True, sharey=True)
        fig.set_size_inches(6, len(ts_names) * 1.25)
        for node in system:
            for i, name in enumerate(ts_names):
                xs, ys = node.get_time_series_x_y(name)
                if time_range:
                    try:
                        xs, ys = zip(
                            *[
                                (x, y)
                                for x, y in zip(xs, ys)
                                if (x >= time_range[0] and x <= time_range[1])
                            ]
                        )
                    except ValueError:
                        xs = []
                        ys = []
                try:
                    if isinstance(ys[0], bool):
                        new_ys = []
                        new_xs = []
                        for x, y in zip(xs, ys):
                            new_ys.extend([not y, y])
                            new_xs.extend([x, x])
                        xs = new_xs
                        ys = new_ys
                except IndexError:
                    pass
                if len(xs) == 0:
                    try:
                        ys.append(0)
                        xs.append(time_range[0])
                    except TypeError:
                        xs[0] = 0
                        pass
                if time_range is not None:
                    try:
                        if xs[0] > time_range[0]:
                            val = ys[0]
                            ys.insert(0, val)
                            xs.insert(0, time_range[0])
                        if xs[-1] < time_range[1]:
                            val = ys[-1]
                            ys.append(val)
                            xs.append(time_range[1])
                    except IndexError:
                        pass
                if node == system[-1]:
                    axs[i].plot(
                        xs,
                        ys,
                        label=f"Node {node.get(StatType.NODE_ID)}",
                        linestyle=":",
                    )
                else:
                    axs[i].plot(xs, ys, label=f"Node {node.get(StatType.NODE_ID)}")

        for ax, row in zip(axs[range(len(ts_names))], short_names):
            ax.set_ylabel(row, rotation=90, size="small")
            ax.set_yticks([0, 1])
            try:
                ax.set_xlim(time_range[0], time_range[1])
            except TypeError:
                pass
        k = 0
        num_handles_labels = 0
        while num_handles_labels < len(system) - 1:
            handles, labels = axs[k].get_legend_handles_labels()
            num_handles_labels += len(labels)
            k += 1
        axs[0].legend(
            handles,
            labels,
            loc="lower center",
            bbox_to_anchor=(0.5, 1.0),
            ncol=5,
            fancybox=True,
            shadow=True,
        )
        # plt.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=2, fancybox=True, shadow=True)
        plt.xlabel("Time (ms)")
        plt.tight_layout()
        plt.savefig(f"{self.save_fig_dir}mac_states.pdf")
        plt.close()

    def plot_macstates_vs_time_slider(self, system=None, time_range: Tuple = None):
        """
        Creates a mac_state vs time plot for each node in a system
        """
        ts_names = [
            StatType.MAC_IS_SENDING,
            StatType.MAC_IS_TRANSMITTING,
            StatType.MAC_IS_LISTENING,
            StatType.MAC_IS_RECEIVING,
        ]
        short_names = ["Sending", "Transmitting", "Listening", "Receiving"]
        fig, axs = plt.subplots(nrows=len(ts_names), sharex=True, sharey=True)
        plt.subplots_adjust(bottom=0.25)
        fig.set_size_inches(6, len(ts_names) * 1.25)
        for node in system:
            for i, name in enumerate(ts_names):
                xs, ys = node.get_time_series_x_y(name)
                if time_range:
                    try:
                        xs, ys = zip(
                            *[
                                (x, y)
                                for x, y in zip(xs, ys)
                                if (x >= time_range[0] and x <= time_range[1])
                            ]
                        )
                    except ValueError:
                        xs = []
                        ys = []
                try:
                    if isinstance(ys[0], bool):
                        new_ys = []
                        new_xs = []
                        for x, y in zip(xs, ys):
                            new_ys.extend([not y, y])
                            new_xs.extend([x, x])
                        xs = new_xs
                        ys = new_ys
                except IndexError:
                    pass
                if len(xs) == 0:
                    try:
                        ys.append(0)
                        xs.append(time_range[0])
                    except TypeError:
                        xs[0] = 0
                        pass
                if time_range is not None:
                    try:
                        if xs[0] > time_range[0]:
                            val = ys[0]
                            ys.insert(0, val)
                            xs.insert(0, time_range[0])
                        if xs[-1] < time_range[1]:
                            val = ys[-1]
                            ys.append(val)
                            xs.append(time_range[1])
                    except IndexError:
                        pass
                if node == system[-1]:
                    axs[i].plot(
                        xs,
                        ys,
                        label=f"Node {node.get(StatType.NODE_ID)}",
                        linestyle=":",
                    )
                else:
                    axs[i].plot(xs, ys, label=f"Node {node.get(StatType.NODE_ID)}")

        for ax, row in zip(axs[range(len(ts_names))], short_names):
            ax.set_ylabel(row, rotation=90, size="small")
            ax.set_yticks([0, 1])
            try:
                ax.set_xlim(time_range[0], time_range[1])
            except TypeError:
                pass
        k = 0
        num_handles_labels = 0
        while num_handles_labels < len(system) - 1:
            handles, labels = axs[k].get_legend_handles_labels()
            num_handles_labels += len(labels)
            k += 1
        axs[0].legend(
            handles,
            labels,
            loc="lower center",
            bbox_to_anchor=(0.5, 1.0),
            ncol=5,
            fancybox=True,
            shadow=True,
        )
        # plt.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=2, fancybox=True, shadow=True)
        plt.xlabel("Time (ms)")

        xmin, xmax, ymin, ymax = ax.axis()  # +10
        end_time = xmax
        ax_time = fig.add_axes([0.2, 0.1, 0.65, 0.03])
        stime = Slider(ax_time, "Time (ms)", 0, end_time, valstep=10, color="green")

        def update(val):
            ax = axs[0]
            pos = stime.val
            xmin, xmax, ymin, ymax = ax.axis()  # +10
            ax_width = xmax - xmin
            if ax_width > 1000:
                ax_width = 100
            ax.axis([pos, pos + ax_width, -0.1, 1.1])  # +10
            fig.canvas.draw_idle()

        ax_b1 = fig.add_axes([0.225, 0.025, 0.1, 0.04])
        ax_b2 = fig.add_axes([0.375, 0.025, 0.1, 0.04])
        button_inc_range = Button(ax_b1, " + Range", hovercolor="0.975")
        button_dec_range = Button(ax_b2, " - Range", hovercolor="0.975")
        ax_b3 = fig.add_axes([0.525, 0.025, 0.1, 0.04])
        ax_b4 = fig.add_axes([0.675, 0.025, 0.1, 0.04])
        button_shift_left = Button(ax_b3, " Left ", hovercolor="0.975")
        button_shift_right = Button(ax_b4, " Right ", hovercolor="0.975")
        ax_b5 = fig.add_axes([0.85, 0.955, 0.1, 0.04])
        button_save = Button(ax_b5, "Save", hovercolor="0.975")

        def increase_range(val):
            ax = axs[0]
            increase_val = 20
            xmin, xmax, ymin, ymax = ax.axis()
            ax.axis([xmin, xmax + increase_val, -0.1, 1.1])  # +10
            fig.canvas.draw_idle()

        def decrease_range(val):
            ax = axs[0]
            decrease_val = 20
            xmin, xmax, ymin, ymax = ax.axis()
            if xmax - xmin > decrease_val:
                ax.axis([xmin, xmax - decrease_val, -0.1, 1.1])  # +10
            else:
                print("WARNING: Cannot decrease range anymore")
            fig.canvas.draw_idle()

        def shift_left(val):
            ax = axs[0]
            shift_val = 10
            xmin, xmax, ymin, ymax = ax.axis()  # +10
            ax.axis([xmin - shift_val, xmax - shift_val, -0.1, 1.1])  # +10
            fig.canvas.draw_idle()

        def shift_right(val):
            ax = axs[0]
            shift_val = 10
            xmin, xmax, ymin, ymax = ax.axis()  # +10
            ax.axis([xmin + shift_val, xmax + shift_val, -0.1, 1.1])  # +10
            fig.canvas.draw_idle()

        def save_plot(val):
            # plt.savefig(f'{self.save_fig_dir}mac_states.pdf')
            xmin, xmax, ymin, ymax = ax.axis()  # +10
            self.plot_macstates_vs_time(system=system, time_range=(xmin, xmax))

        stime.on_changed(update)
        button_inc_range.on_clicked(increase_range)
        button_dec_range.on_clicked(decrease_range)
        button_shift_left.on_clicked(shift_left)
        button_shift_right.on_clicked(shift_right)
        button_save.on_clicked(save_plot)

        ax.ticklabel_format(useOffset=False)
        plt.show()

        plt.savefig(f"{self.save_fig_dir}mac_states.png")
        plt.close()

    def net_traffic_bar_graph(self, nodes: List[int] = None):
        # labels = ['Node0', 'Node1', 'Node2', 'Node3', 'Node4']
        labels = []

        packets_generated = []
        packets_sent_app = []
        packets_received_app = []
        packets_sent_ill = []
        packets_received_net = []
        for node in range(len(nodes)):
            # packets_generated.append([])
            packets_generated.append(0)
            # packets_sent_app.append([])
            packets_sent_app.append(0)
            # packets_received_app.append([])
            packets_received_app.append(0)
            # packets_sent_ill.append([])
            packets_sent_ill.append(0)
            # packets_received_net.append([])
            packets_received_net.append(0)
            labels.append(f"Node{nodes[node]}")
        for series_metadata, series_result in self.results.items():
            for x_val, sim_results in series_result.items():
                for sim in sim_results:
                    i = 0
                    for node in sim:
                        # print(packets_generated, packets_generated[i], type(packets_generated[i]))#, packets_generated[i][0], type(packets_generated[i][0]))
                        packets_generated[i] += node.get(StatType.PACKETS_GENERATED)
                        packets_sent_app[i] += node.get(StatType.PACKETS_SENT_APP)
                        packets_received_app[i] += node.get(
                            StatType.PACKETS_RECEIVED_APP
                        )
                        packets_sent_ill[i] += node.get(StatType.PACKETS_SENT_ILL)
                        packets_received_net[i] += node.get(
                            StatType.PACKETS_RECEIVED_NET
                        )
                        i += 1
        for i in range(len(nodes)):
            packets_generated[i] /= self.trials
            packets_sent_app[i] /= self.trials
            packets_received_app[i] /= self.trials
            packets_sent_ill[i] /= self.trials
            packets_received_net[i] /= self.trials

        x = np.arange(len(labels))  # the label locations
        width = 0.1  # the width of the bars

        fig, ax = plt.subplots()
        ax.bar(
            x - 2 * (width), packets_generated, width, label="Generated", color="k"
        )
        ax.bar(
            x - (width), packets_sent_app, width, label="App Sent", color="r"
        )
        ax.bar(x, packets_sent_ill, width, label="ILL Sent", color="m")
        ax.bar(
            x + (width), packets_received_app, width, label="App Rx", color="b"
        )
        ax.bar(
            x + 2 * (width), packets_received_net, width, label="Net Rx", color="c"
        )

        # Add some text for labels, title and custom x-axis tick labels, etc.
        ax.set_ylabel("Packets")
        ax.set_title("Packets across nodes")
        ax.set_xticks(x, labels)
        ax.legend()

        fig.tight_layout()

        plt.savefig(self.save_fig_dir + "bar_graph.png")

    def packet_delivery_ratio_bar_graph(
        self,
        exp_index: int = 0,
        series_id=0,
        XVal="Unknown",
        save_differentiator="",
        format="pdf",
    ):
        plt.rcParams.update({"font.size": 22})
        experiment = ResultsParser.getExperiment(self.results, exp_index)
        if type(series_id) == type(0):
            series_results = ResultsParser.getSeriesResultByIndex(experiment, series_id)
        else:
            series_results = ResultsParser.getSeriesResultByMetadataKey(
                experiment, series_id
            )
        if XVal == "Unknown" and (ResultsParser.getAllXVals(experiment) > 1):
            raise Exception(
                "XVal was set to 'Unknown' (default), but there are more than one XVal in the results"
            )
        trials = ResultsParser.getAllTrials(series_results, XVal)
        num_trials = len(trials)
        with trials[0] as t:
            num_nodes = len(t.results)
        sources = {}
        packets_generated_top = {}
        packets_generated_bottom = {}
        for i in range(num_nodes):
            sources[i] = [0] * num_nodes
            packets_generated_top[i] = [0] * num_nodes
            packets_generated_bottom[i] = [0] * num_nodes
        for stats_list in trials:
            for node in stats_list:
                id = node.get(StatType.NODE_ID)
                trails = node.get_time_series(StatType.NETWORK_PACKET_TRAILS)
                for packet in trails:
                    src = int(packet[1]["source_node"])
                    sources[id][src] += 1
        for i in range(num_nodes):
            for j in range(num_nodes):
                sources[i][j] = round(sources[i][j] / num_trials)
        for stats_list in trials:
            for node in stats_list:
                id = node.get(StatType.NODE_ID)
                all_gen = node.get_list(StatType.PACKETS_GENERATED_DESTINATIONS)
                for dest in all_gen:
                    packets_generated_top[id][dest] += 1
        for i in range(num_nodes):
            for j in range(num_nodes):
                packets_generated_top[i][j] = round(
                    packets_generated_top[i][j] / num_trials
                )

        for i in range(num_nodes):
            for j in range(num_nodes):
                packets_generated_bottom[i][j] = sources[i][j]
                packets_generated_top[i][j] -= sources[i][j]

        labels = []
        for i in range(num_nodes):
            labels.append(f"{i}")
        x = np.arange(len(labels))  # the label locations
        width = 0.105  # the width of the bars
        fig, ax = plt.subplots()
        ax.bar(
            x - 3 * (width),
            sources[0],
            width,
            label="0",
            color="tab:red",
            edgecolor="k",
        )
        ax.bar(
            x - 2 * (width),
            sources[1],
            width,
            label="1",
            color="darkorange",
            edgecolor="k",
        )
        ax.bar(
            x - (width), sources[2], width, label="2", color="gold", edgecolor="k"
        )
        ax.bar(
            x, sources[3], width, label="3", color="limegreen", edgecolor="k"
        )
        ax.bar(
            x + (width),
            sources[4],
            width,
            label="4",
            color="deepskyblue",
            edgecolor="k",
        )
        ax.bar(
            x + 2 * (width),
            sources[5],
            width,
            label="5",
            color="mediumorchid",
            edgecolor="k",
        )

        hatch = "//"
        ax.bar(
            x - 3 * (width),
            packets_generated_top[0],
            width,
            bottom=packets_generated_bottom[0],
            label="Undelivered",
            color="darkgrey",
            edgecolor="k",
            hatch=hatch,
        )
        ax.bar(
            x - 2 * (width),
            packets_generated_top[1],
            width,
            bottom=packets_generated_bottom[1],
            color="darkgrey",
            edgecolor="k",
            hatch=hatch,
        )
        ax.bar(
            x - (width),
            packets_generated_top[2],
            width,
            bottom=packets_generated_bottom[2],
            color="darkgrey",
            edgecolor="k",
            hatch=hatch,
        )
        ax.bar(
            x,
            packets_generated_top[3],
            width,
            bottom=packets_generated_bottom[3],
            color="darkgrey",
            edgecolor="k",
            hatch=hatch,
        )
        ax.bar(
            x + (width),
            packets_generated_top[4],
            width,
            bottom=packets_generated_bottom[4],
            color="darkgrey",
            edgecolor="k",
            hatch=hatch,
        )
        ax.bar(
            x + 2 * (width),
            packets_generated_top[5],
            width,
            bottom=packets_generated_bottom[5],
            color="darkgrey",
            edgecolor="k",
            hatch=hatch,
        )

        plt.axhline(10000 / 30, color="k")

        # Add some text for labels, title and custom x-axis tick labels, etc.
        ax.set_ylabel("Delivered and Undelivered Packets")
        ax.set_xlabel("Source Node")
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 850)
        ax.legend(
            loc="lower center",
            bbox_to_anchor=(0.48, 1.02),
            ncol=8,
            labelspacing=0.5,
            columnspacing=1,
            fancybox=True,
            shadow=False,
        )
        plt.gcf().set_size_inches(12, 8)
        plt.savefig(
            self.save_fig_dir + f"packet_delivery_ratio{save_differentiator}.{format}"
        )
        plt.close()
