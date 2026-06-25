from lure.lure import Lure
from lure.plotter import Plotter
import matplotlib as mpl

mpl.rcParams.update(mpl.rcParamsDefault)
from lure.node.stats import StatType


# Example of a mac_state interactive plot
if __name__ == "__main__":
    # Setup Lure
    simulator = Lure(
        config_dir="config",
        top_config_file="lure.json",
        output_dir="output",
        resume=True,
    )
    results = simulator.run()
    data = simulator.load_results(output_dir="output")
    plotter = Plotter(
        trials=1,
        results=data,
        output_dir="output/figures/time_series/",
        extension="pdf",
    )
    stats = [
        StatType.MAC_IS_SENDING,
        StatType.MAC_IS_TRANSMITTING,
        StatType.MAC_IS_LISTENING,
        StatType.MAC_IS_RECEIVING,
    ]
    nodes = [0, 1]
    plotter.plot_time_series(
        names=stats, series_metadatakey="2_2", xval=0.2, node_ids=nodes
    )
    # Interactive plot — uncomment to explore data in a GUI window.
    # Instructions:
    #   1) Set what stats you want to plot. 0th index is the top of the stack of subplots.
    #   2) Use plot_time_series_interactive(). Give the stat name and which nodes to track (by node_id).
    #   3) The -/+ Range buttons decrease/increase the range of the x-axis by 25 ms
    #   4) The L/R buttons shift the window of the plot left and right by 10 ms
    #   5) The Save button saves the current window to a PDF in Plotter's output directory
    # plotter.plot_time_series_interactive(
    #     names=stats, series_metadatakey="2_2", xval=0.2, node_ids=nodes
    # )
