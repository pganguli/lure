from lure.lure import Lure
from lure.node.stats import StatType
from lure.plotter import Plotter

results = Lure.load_results("example_output")

ts_names = [
    StatType.HARVESTER_CHARGING_POWER,
    StatType.STORAGE_VOLTAGE,
    StatType.NODE_STATE,
    StatType.MAC_IS_TRANSMITTING,
    StatType.MAC_IS_RECEIVING,
]

options = {
    StatType.HARVESTER_CHARGING_POWER: {"discrete": True},
    StatType.LMP_ON_TIME: {"discrete": True},
}

plotter = Plotter(results=results)
plotter.plot_time_series(names=ts_names, options=options)
plotter.plot_time_series(names=ts_names, options=options, time_range=(0, 11000))
plotter.plot_stat_list_distribution(StatType.PACKET_ARRIVAL_INTERVALS)
