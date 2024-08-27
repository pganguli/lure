import copy
import pickle
from multiprocessing import Pool
import os
from typing import Dict, Hashable, List, Tuple

from lure.config.configuration import Config, DataSeriesConfig, ExperimentConfig, LoggerConfig
from lure.energy.energy_model import EnergyModel, EnergyModelConfig
from lure.node.sensor_node import SensorNode, SensorNodeConfig
from lure.results import SIMULATION_RESULT_FILENAME, ExperimentResult, SeriesResult, SimulationResult
from lure.simulation import Simulation

from alive_progress import alive_bar

class DataSeriesMetadata:
    """Metadata used to key into a ExperimentResult object.
    Deprecated but kept for backwards compatibility.
    """
    def __init__(self, config: DataSeriesConfig) -> None:
        self.plot_config = None
        self.key = None
        config.extract("plot_config", self, dict())
        config.extract("key", self, "default")

        self.x_values: List[XValue] = []


class DataSeries:
    """A series of an experiment
    """
    def __init__(self, config: DataSeriesConfig, energy_model_config: EnergyModelConfig):
        self.plot_config = None
        self.key = None

        config.extract("plot_config", self, dict())
        config.extract("key", self, "default")

        self.x_values: List[Hashable] = []
        self.nodes = [] # [[(ivar_val, SensorNode), (ivar_val, SensorNode)...], [(), ()]...]
        self.energy_models = dict()
        other_nodes_list = []
        for node_config in config.nodes:
            node_dicts = Config.get_dict_permutations(node_config.config)
            if node_dicts:
                self.nodes.append([])
                for ivar_val, d in node_dicts.items():
                    # if ivar_val not in self.nodes:
                    #     self.nodes[ivar_val] = []
                    # self.nodes[ivar_val].append(SensorNode(SensorNodeConfig(d)))
                    self.nodes[-1].append((ivar_val, SensorNode(SensorNodeConfig(d))))
            else:
                other_nodes_list.append(SensorNode(node_config))

        try:
            #series_len = max(len(v) for v in self.nodes.values())
            series_len = max(len(n) for n in self.nodes)
        except ValueError:
            series_len = 0
            
        if series_len > 0:
            print(f'Info: found independent variables for SensorNode (and will not look in EnergyModel).')
            #x_values = list(self.nodes.keys())
            # Uses the independent var values from the first node as the x values...
            self.x_values = [t[0] for t in self.nodes[0]]

            # Fill in "other" nodes, i.e. nodes that did not have an independent var list
            for node in other_nodes_list:
                self.nodes.append([])
                for _ in range(series_len):
                    self.nodes[-1].append((None, copy.deepcopy(node)))

            # Add filler nodes if needed
            for i, node_perms in enumerate(self.nodes):
                if len(node_perms) < series_len:
                    print(f'Warning: inconsistent independent var lengths found ({series_len} and {len(node_perms)}). Adding some filler nodes.')
                    for _ in range(series_len - len(node_perms)):
                        self.nodes[i].append((None, copy.deepcopy(self.nodes[i][-1][1])))

            # for ivar_val, node_list in self.nodes.items():
            #     list_copy = copy.deepcopy(other_nodes_list)
            #     node_list.extend(list_copy)
            #     if len(node_list) < series_len:
            #         print(f'Warning: inconsistent independent var lengths found ({series_len} and {len(node_list)}). Adding some filler nodes.')
            #         for _ in range(series_len - len(node_list)):
            #             node_list.append(copy.deepcopy(other_nodes_list[-1]))
            
        else:
            energy_model_dicts = Config.get_dict_permutations(energy_model_config.config)
            if energy_model_dicts:
                for ivar_val, d in energy_model_dicts.items():
                    self.energy_models[ivar_val] = Config.instantiate_from_dict(d, 'lure.energy')
                self.x_values = list(self.energy_models.keys())
                
        
        if not self.nodes and not self.energy_models:
            print(f'Info: no independent variables detected for SensorNode or EnergyModel. XValue in SeriesResult will be "None".')
            for node in other_nodes_list:
                self.nodes.append([(None, node)])
            #self.nodes["Unknown"] = other_nodes_list
            self.energy_models[None] = Config.instantiate_from_dict(energy_model_config.config, 'lure.energy')
            self.x_values.append(None)
        elif not self.energy_models:
            self.energy_models = { k: Config.instantiate_from_dict(energy_model_config.config, 'lure.energy') for k in self.x_values }
        elif not self.nodes:
            #self.nodes = { k: other_nodes_list for k in x_values }
            for node in other_nodes_list:
                self.nodes.append([(k, copy.deepcopy(node)) for k in self.x_values])


    def get_key(self):
        """Getter for the key of a DataSeriesMetadata object corresponding to this DataSeries object

        :return: Key for the metadata of this series 
        """
        return self.key

def _run_sim(energy_model: EnergyModel, nodes: List[SensorNode], logger_config: LoggerConfig, max_time: int, max_packets: int, output_dir: str, seed=1):
    """Runs a simulation

    :param energy_model: Energy model for the simulation
    :type energy_model: EnergyModel
    :param nodes: Nodes in the simulation
    :type nodes: List[SensorNode]
    :param logger_config: Configuration for the logger of this simulation
    :type logger_config: LoggerConfig
    :param max_time: Maximum time to be spent in the simulation
    :type max_time: int
    :param max_packets: Maximum successful packet transmissions in the simulation
    :type max_packets: int
    :param output_dir: Output directory for results
    :type output_dir: str
    :param seed: Trial number, defaults to 1
    :type seed: int, optional
    """
    # TODO: move the directory/file work to corresponding Result class
    results_dir = f'{output_dir}/{seed}'
    if os.path.isfile(f'{results_dir}/{SIMULATION_RESULT_FILENAME}'):
        return
    os.makedirs(results_dir, exist_ok=True)
    sim = Simulation(energy_model, nodes, logger_config, max_time, max_packets, output_dir=results_dir, seed=seed)

    sim.run()


class Experiment:
    """Experiment of a Lure object 
    """

    def __init__(self, config: ExperimentConfig, output_dir: str = 'output/results'):
        self.num_trials = None
        self.max_time = None
        self.max_packets = None
        config.extract("num_trials", self, 1)
        config.extract("max_time", self, 3600000)
        config.extract("max_packets", self, 0)

        self.output_dir = output_dir

        self.logger_config = config.logger
        self.series = [DataSeries(ser, config.energy_model) for ser in config.series]

        self.results = ExperimentResult()

    def run_series(self, series: DataSeries, pool: Pool = None, progress_bar=None) -> SeriesResult:
        """Runs simulations for a data series

        :param series: The series to run simulations for
        :type series: DataSeries
        :param pool: Used for multi-processing, defaults to None
        :type pool: Pool, optional
        :param progress_bar: Used for running a simulation with a progress bar, defaults to None
        """
        results_dir = f'{self.output_dir}/{series.get_key()}'
        os.makedirs(results_dir, exist_ok=True)

        series_result = SeriesResult(series.get_key(), results_dir, series.plot_config)

        for i, x in enumerate(series.x_values):
            nodes = [n[i][1] for n in series.nodes]
            if progress_bar != None:
                    progress_bar.text(f'series=\'{series.get_key()}\', xval={x}')
            if pool:
                args = [[series.energy_models[x], nodes, self.logger_config, self.max_time, self.max_packets, f'{results_dir}/{x}', k] for k in range(self.num_trials)]
                pool.starmap(_run_sim, args)
            else:
                for j in range(self.num_trials):
                    _run_sim(series.energy_models[x], nodes, self.logger_config, self.max_time, self.max_packets, f'{results_dir}/{x}', seed=j)
            if progress_bar != None:
                progress_bar()

            for j in range(self.num_trials):
                series_result.add_simulation(x, j)

        return series_result

    def run(self, pool: Pool = None, progress_bar=None) -> ExperimentResult:
        """Run an experiment

        :param pool: Used for multi-processing, defaults to None
        :type pool: Pool, optional
        :param progress_bar: Used for displaying a progress bar, defaults to None
        """
        for p in self.series:
            self.results.add_series(self.run_series(p, pool, progress_bar))

        return self.results
