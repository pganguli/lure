from lure.lure import Lure
from lure.plotter import Plotter

results = Lure.load_results()

plotter = Plotter(results=results)
# plotter.plot_vs_x_y(postfix='', xtype='extratime', ytype='extratime', ztype='delay', surface3d=True)
plotter.plot_vs_x_y(
    postfix="", xtype="extratime", ytype="extratime", ztype="throughput", surface3d=True
)
