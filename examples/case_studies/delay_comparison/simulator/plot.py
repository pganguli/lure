from lure.lure import Lure
from lure.plotter import Plotter


data = Lure.load_results(output_dir="output")

plotter = Plotter(results=data, extension="pdf")
plotter.plot_y_vs_x(
    xtype="lambda",
    ytype="delay",
    legend_placement="best",
    data_type="median",
    show_ci=True,
)
