# Lure
Lure is a SimPy-based simulator designed for simulating and evaluating batteryless intermittent sensor networks (BISNs).

## Installation

### From source
1. Clone from GitLab

	`git clone [TODO]`

1. Set up and activate a Python virtual environment with Python 3
1. Install Lure in developer mode (run from the directory containing this README)

	`python -m pip install -e .`

## Using Lure
These instructions assume you are using Lure for a research project and will be writing custom subclasses of components that may eventually be added to Lure's main branch.
1. Install from source, as described above.
1. Make sure your virtual environment is activated.
1. In GitLab, create a branch `$BRANCH` named after your project (Repository -> Branches -> New Branch).
1. Check out your branch locally.

	`git fetch`

	`git checkout $BRANCH`

1. Project-specific configuration and run/plotting scripts will NOT be added to the Lure repo. Instead, create a new project repo and clone this project to the `projects/` subdirectory of your local copy of Lure. To get started with your project, look at one of the other lure_projects, or the Lure examples under `examples/`.
1. From your project directory, verify your setup is correct by running `python -m lure` or `python run.py` (assuming you copied in an example or another project). This should complete successfully, create an output directory, etc.

1. You should be able to add most custom functionality needed for your project by subclassing existing simulator components. As an example, let's say you want to implemement a constant charging rate harvester.

	1. Make a new file with a copy of your chosen parent class. E.g., copy the `Harvester` class from `src/lure/node/power/harvester.py` into a new file `src/lure/node/power/constant_harvester.py`.
	1. Give your new subclass a new name and add inheritance. E.g.:
	
		`class ConstantHarvester(Harvester):`

	1. Most or all of the methods in the top-level class are called by other components in the simulator. As much as possible, leave functionality up to the parent class via `super()`, or by simply deleting methods that you don't need to override.

	1. To get your subclass to work with the configuration system, there are a few things you need to do:
		1. Your `__init__()` method should accept a `Config` (or subclass of `Config`) as its first and only parameter.

		1. You can use `config.extract()` to pull parameters out of the `Config` object and save them as instance variables. For example, `Harvester` extracts the parameter `loss_factor` from the config, which means the configuration JSON for a `Harvester` can/should specify `loss_factor`.

		1. You also need to register your subclass with the package. Edit `__init__.py` in the corresponding package (e.g. `src/lure/node/power/__init__.py`) and add an import for your subclass (e.g. `from lure.node.power.constant_harvester import ConstantHarvester`).

		1. Now in your configuration JSON, you can specify and configure your subclass as a JSON object with `"class": "$SUBCLASS_NAME"` and parameters `"$PARAM_NAME": "$PARAM_VAL"`. E.g.:
			```
			{
				"class": "ConstantHarvester",
				"constant_rate": 0.001
			}
			```
		
		1. This goes in the corresponding place in your tree of JSON configuration, e.g. the `harvester` object of the `power_supply` object of a `node` object.

1. We recommend creating a separate `plot.py` script for plotting. Lure automatically saves results from experiments as pickle files in the output directory (see below). You can reload the results for plotting using `Lure.load_results()`. The `Plotter` class in `src/lure/plotter.py` has some out-of-the-box plotting functionality, and examples of how to unpack and interpret the results.

1. Configure your experiment(s) via JSON in your project `config` directory. If you have different types of experiments to run, you may find it easiest to create separate subdirectories, each with their own `config` directory and (optionally) `run.py` script. For configuration examples, in addition to `examples/*/config/`, see `src/lure/config/default/`. These are the default configurations, which are used as the base for all configurations. Any values that you do not specify in your configuration will default to the values found here. Otherwise, configuration in general works with a type/overrides system. A component specified by `type` corresponds to a JSON file called `$TYPE_$COMPONENT.json`. Any parameters specified alongside the `type` will override parameters loaded from the type file. In theory, from any level of configuration, you should be able to use this system to specify overrides to any arbitrary deeper level of configuration (please file an issue if this does not work in practice).

1. You may want to periodically bring in new features/fixes added to main. Since bringing in upstream changes is equivalent to updating your version of the simulator, we recommend using `git merge` (instead of `git rebase`) for this.

	```
	git fetch origin main
	git checkout $BRANCH
	git merge origin/main
	```

1. Lure supports a logging system within the lure_logger module which exports its data to a text file in the output directory. LureLogger enables classes to create their own log allowing Lure to be configured to log information on a class-by-class basis. In the logger configuration file, each Log can be assigned one of 5 levels: CRITICAL, ERROR, WARNING, INFO, and DEBUG (in order of descending importance). Lower levels include all the information from levels above it. For example, if MAC was assigned a level of DEBUG while all other logs are set to ERROR, this would cause Lure to log all information for MAC, but only ERROR and CRITICAL information for everything else. Moreover, LureLogger can be configured to separate the logs by node by setting split_logs to True. This creates a separate text file to improve readability in large scale experiments. Finally, by default Lure buffers all logging until the end of a simulation to increase simulation speed. However, buffer_writes can be set to False to conduct "live logging" for the need to debug simulations that have errors. Please see '/src/lure/config/default/*_logger.json for examples of logger configurations.

1. If you need to request features from the simulator core (anything outside your custom subclasses), or find bugs in the core, please open an issue in GitLab.
 
## Results and Plotting
Lure saves all results on disk in the format `$output/results/$exp/$ser/$xval/$seed/results.p`, where:
- `$output` is the Lure output directory (default `output/`)
- `results` is the results subdirectory, corresponding to a `LureResults` object, which contains a list of `ExperimentResults`
- `$exp` is the experiment index, corresponding to an `ExperimentResult` object, which contains a dictionary of `SeriesResult` objects mapped to series keys
- `$ser` is the series key, corresponding to a `SeriesResult` object, which contains a dictionary of lists of `SimulationResult` objects mapped to independent variable values
- `$xval` is the independent variable value in the series, corresponding to a list of `SimulationResult` objects
- `$seed` is the seed of the specific simulation trial, corresponding to a single `SimulationResult` object, which contains a list of `Stats` objects
- `results.p` is a pickled list of the `Stats` objects for each node in the trial

This format mirrors the Lure configuration, and the corresponding `LureResults` object hierarchy is built as Lure runs. This object is pickled and written to disk as `results/lure_results.p`.

However, this pickled version only contains *paths* to `SimulationResult` objects, not the objects themselves. When Lure runs, each `Simulation` writes its own `results.p` file, without adding the results to the `LureResults`. This minimizes the amount of data passed between processes and the amount of memory needed to run Lure.

When Lure's results are loaded (i.e. using `Lure.load_results()`), the `LureResults` object is unpickled and returned immediately. The actual simulation results are lazily loaded from the `results.p` file when iterating through the `SimulationResult` objects. They can also be loaded using a Python `with` statement.

Each of the results objects are iterable. The suggested method for iterating through Lure results is as follows:
```python
results = Lure.load_results()

for exp_result in results:
    for series_result in exp_result:
		# series_result.key is the series_key
		# You can also iterate through exp_result
		# as a dictionary using exp_result.items()
        for sim_results in series_result:
			# series_result.x_values is the x-values for the series
			# These are also used as keys to the sim
			# results, and you can use series_result.items()
			# to iterate with them
            for sim_result in sim_results:
                for node_stats in sim_result:
                    # Take ALL the stats you want here.
					# You don't want to repeat this
					# iteration, because this is where
					# the results are loaded from disk.
```

The class `StatParser` within src/lure/node/stats.py contains convenience methods for calculating advanced statistics from the raw data taken from the simulator.

The examples in the `examples` directory have some starter templates for how plotting functions can implemented.

## Configurations

## Contributing to core
TODO

## Docs
See the README in `docs/`.