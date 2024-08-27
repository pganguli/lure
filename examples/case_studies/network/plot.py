from lure.lure import Lure
from lure.plotter_special import PlotterSpecial
from lure.results_parser import ResultsParser
import time
import os

# Unpack the data
simulator = Lure(config_dir='config', top_config_file='top.json', output_dir='output', resume=True, progress_bar=True)
results = simulator.load_results(output_dir='output')

# Plot the data
i = 0
for exp_index in range(len(results.experiment_results)):
    experiment = ResultsParser.getExperiment(results, exp_index)
    xvals = ResultsParser.getAllXVals(experiment)
    num_trials = ResultsParser.getNumTrials(experiment)
    series_key = '0.001-traffic'
    series = ResultsParser.getSeriesResultByMetadataKey(experiment, series_key)
    figures_dir ='figures/'
    os.makedirs(figures_dir, exist_ok=True)
    plotter = PlotterSpecial(trials=num_trials, results=results, dir=figures_dir)
    for xval in xvals:
        trials = ResultsParser.getAllTrials(series, xval)
        save_diff = f'_{xval}'
        plotter.packet_delivery_ratio_bar_graph(exp_index, series_key, xval, save_differentiator=save_diff, format='pdf')
    i+=1