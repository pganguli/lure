import pickle
from typing import Hashable, List, Any

from lure.node.stats import Stats

LURE_RESULTS_FILENAME = 'lure_results.p'
SIMULATION_RESULT_FILENAME = 'results.p'

class SimulationResult:
    
    def __init__(self, output_dir: str, seed: int):
        super().__init__()
        self.seed = seed
        self.results: List[Stats] = None
        self.results_filename = f'{output_dir}/{self.seed}/{SIMULATION_RESULT_FILENAME}'

    def write(self):
        with open(self.results_filename, 'wb') as f:
            pickle.dump(self.results, f)

    def _open(self):
        if self.results is None:
            with open(self.results_filename, 'rb') as f:
                self.results = pickle.load(f)

    def _close(self):
        self.results = None

    def __iter__(self):
        self._open()
        self._i = 0
        return self

    def __next__(self):
        try:
            next = self._i
            self._i += 1
            return self.results[next]
        except IndexError:
            self._close()
            raise StopIteration

    def __enter__(self):
        self._open()
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self._close()

class SeriesResult:

    def __init__(self, key: str, output_dir: str, plot_config: dict = dict()):
        self.key = key
        self.plot_config = plot_config
        self.sim_results: dict[Hashable, List[SimulationResult]] = {}
        self.output_dir = output_dir

    @property
    def x_values(self):
        return list(self.sim_results.keys())

    def add_simulation(self, x_value: Hashable, seed: int):
        if x_value not in self.sim_results:
            self.sim_results[x_value] = []
        self.sim_results[x_value].append(SimulationResult(f'{self.output_dir}/{x_value}', seed))

    def items(self):
        return self.sim_results.items()

    def __iter__(self):
        self._keys = self.x_values
        self._i = 0
        return self
    
    def __next__(self):
        try:
            next = self._i
            self._i += 1
            return self.sim_results[self._keys[next]]
        except IndexError:
            raise StopIteration

class ExperimentResult:
    
    def __init__(self):
        self.series_results: dict[str, SeriesResult] = {}

    def add_series(self, series_result: SeriesResult):
        self.series_results[series_result.key] = series_result

    def items(self):
        return self.series_results.items()

    def __iter__(self):
        self._keys = [k for k in self.series_results.keys()]
        self._i = 0
        return self
    
    def __next__(self):
        try:
            next = self._i
            self._i += 1
            return self.series_results[self._keys[next]]
        except IndexError:
            raise StopIteration

class LureResults:

    def __init__(self):
        self.experiment_results: List[ExperimentResult] = []

    def add_experiment(self, experiment_result: ExperimentResult):
        self.experiment_results.append(experiment_result)

    def write(self, results_dir: str):
        with open(f'{results_dir}/{LURE_RESULTS_FILENAME}', 'wb') as f:
            pickle.dump(self, f)

    def __iter__(self):
        self._i = 0
        return self

    def __next__(self):
        try:
            next = self._i
            self._i += 1
            return self.experiment_results[next]
        except IndexError:
            raise StopIteration