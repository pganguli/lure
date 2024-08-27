import copy
import importlib
import json
import pkgutil
from typing import Any, Dict, List

from lure.lure_logger import LogLevel

class Config:
    """An object for managing configuration of Lure components."""

    CONFIG_NAME = None
    CONFIG_DIR = './'

    @staticmethod
    def merge_dicts(dest, source):
        """Recursively merges the source dictionary into the destination dictionary
        via deep copying.

        :param dest: Destination dictionary
        :type dest: Dict
        :param source: Source dictionary
        :type source: Dict
        """
        for k, v in source.items():
            if isinstance(v, dict) and k in dest:
                Config.merge_dicts(dest[k], v)
            elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and k in dest and len(v) == len(dest[k]):
                for i, item in enumerate(v):
                    Config.merge_dicts(dest[k][i], item)
            else:
                dest[k] = copy.deepcopy(v)

    @staticmethod
    def get_dict_permutations(d: dict, root: dict = None, keys: List = None) -> Dict[Any, dict]:
        """Recursively searches through a dictionary and finds a list
        (i.e. an independent variable) and builds a new mega-dictionary
        (via deep copying) that contains all permutations of this
        dictionary where the list is replaced by one item from that list.
        
        :param d: Input dictionary
        :type d: Dict[Any, Any]
        :param root: The level of the input dictionary to start at, used during recursion
        :type root: Dict[Any, Any], optional
        :param keys: The trail of keys used to get to the root, used during recursion
        :type keys: List[Any]
        :return: The mega-dictionary of permutations
        :rtype: Dict[Any, dict]
        """
        if not root:
            root = d
        if not keys:
            keys = []
        for k, v in d.items():
            if isinstance(v, list) and not isinstance(v[0], dict):
                dict_of_dicts = { val: copy.deepcopy(root) for val in v }
                for val in v:
                    t = dict_of_dicts[val]
                    for key in keys:
                        t = t[key]
                    t[k] = val
                return dict_of_dicts

            elif isinstance(v, dict):
                keys.append(k)
                branch_dict = Config.get_dict_permutations(v, root, keys)
                keys.pop()
                if branch_dict:
                    return branch_dict
            
        return None

    @staticmethod
    def instantiate_from_dict(d: dict, module: str) -> object:
        """Creates a Lure object from a configuration dictionary

        :param d: Input dictionary, which should contain a key "class" that defines the class of the object
        :type d: Dict[Any, Any]
        :param module: The path of the module the class belongs to, e.g. "lure.node.power"
        :type module: str
        :return: The instantiated object
        :rtype: object
        """
        config = Config(d)
        try:
            mod = importlib.import_module(module)
            obj_class = getattr(mod, config.config["class"])
            return obj_class(config)
        except KeyError:
            print(f'Error: key "class" not found in config dict {d}.')
            return None

    def extract(self, val: str, obj: object, default: Any):
        """Unpacks a value from a Lure object's config dictionary and adds it as an attribute to the object

        :param val: The name of the configuration value
        :type val: str
        :param obj: The Lure object
        :type obj: object
        :param default: The value to assign if the configuration value is not found
        :type default: Any
        """
        try:
            setattr(obj, val, self.config[val])
        except KeyError:
            print(f'Warning: config key {val} not found in instance of {self.__class__}. Using default value of {default}.')
            setattr(obj, val, default)

    def merge_file(self, path: str) -> bool:
        """Merges the config JSON from the given file into this Config.

        :param path: The path of the file to be merged
        :type path: str
        :return: True if successful, false if not
        :rtype: bool
        """
        try:
            with open(path, 'r') as f:
                self.merge_dict(json.load(f))
                return True
        except FileNotFoundError:
            print(f'Warning: file {path} not found.')
            return False

    def merge_type_file(self, type: str) -> bool:
        """Searches for a config file of the given type and, if found,
        merges the JSON in it into this Config.

        :param type: The type of the configuration to search for
        :type type: str
        :return: True if a config file of the given type is found and merged, false if not
        :rtype: bool
        """
        if type == 'default':
            print(f'Warning: using built-in default type for {self.CONFIG_NAME}. If you meant to load a custom type, name it something other than "default".')
            return False
        if self.CONFIG_NAME:
            file = f'{self.CONFIG_DIR}/{type}_{self.CONFIG_NAME}.json'
        else:
            file = f'{self.CONFIG_DIR}/{type}.json'
        return self.merge_file(file)

    def merge_default_config(self):
        """Merges in the default configuration for this Config
        """
        if not self.CONFIG_NAME:
            return
        s = pkgutil.get_data(f'{__package__}.default', f'default_{self.CONFIG_NAME}.json')
        if s:
            self.merge_dict(json.loads(s))
        else:
            print(f'Warning: default json not found for config name "{self.CONFIG_NAME}."')

    def __init__(self, config: dict = dict(), file = None):
        """Creates a new Config object.

        :param config: Initial configuration dictionary
        :type config: Dict, optional
        :param file: JSON file to load configuration from
        :type file: str, optional
        """
        self.config = dict()
        self.merge_default_config()

        if file:
            self.merge_file(file)

        config_copy = copy.deepcopy(config)

        if 'type' in config_copy:
            self.merge_type_file(config_copy['type'])
            del config_copy['type']
            # if 'overrides' in self.config:
            #     self.merge_dict(self.config['overrides'])
            #     del self.config['overrides']

        self.merge_dict(config_copy)
    
    def merge_dict(self, d: dict):
        """Merges the given dictionary into this Config.

        :param d: Dictionary to merge
        :type d: Dict[Any, Any]
        """
        if d is None:
            return

        Config.merge_dicts(self.config, d)

    def get_flattened_config(self) -> Dict[Any, Any]:
        """Returns the dict representation of this Config

        :return: The dict for this Config
        :rtype: Dict[Any, Any]
        """
        return self.config

    def __str__(self):
        return json.dumps(self.get_flattened_config(), indent=4)

class LoggerConfig(Config):
    """A Config object for logging configuration."""

    CONFIG_NAME = 'logger'

    def merge_type_file(self, type: str):
        custom_file_found = super().merge_type_file(type)
        if not custom_file_found:
            print(f'Warning: custom logger type file not found, trying built-in loggers.')
            s = pkgutil.get_data(f'{__package__}.default', f'{type}_{self.CONFIG_NAME}.json')
            if s:
                self.merge_dict(json.loads(s))
                print(f'Using built-in {type} logger.')
                return True
            else:
                print(f'Warning: logger type {type} not found.')
        return custom_file_found

    def get_level(self, component: str) -> LogLevel:
        """Returns the log level of this logger configuration for the given component.

        :param component: The name of the component
        :type component: str
        :return: The configured log level
        :rtype: LogLevel
        """
        try:
            lvl = self.config[component]["level"]
        except:
            print(f'Warning: no level found for {component} in logger config. Using INFO.')
            lvl = "info"
        return LogLevel(lvl)

class StatsConfig(Config):
    """A Config object for Stats collection configuration."""

    CONFIG_NAME = "stats"

class EnergyModelConfig(Config):
    """A Config object for an EnergyModel."""

    CONFIG_NAME = "energy_model"

class SensorNodeConfig(Config):
    """A Config object for a SensorNode."""

    CONFIG_NAME = "node"

    def __init__(self, config: dict, logger_config: LoggerConfig = None, stats_config: StatsConfig = None):
        super().__init__(config)

        if logger_config:
            self.config["logger"] = logger_config.config

        if "logger" not in self.config:
            logger = LoggerConfig()
            self.config["logger"] = logger.config

        
        if stats_config:
            self.stats = stats_config
        elif "stats" in self.config:
            self.stats = StatsConfig(self.config["stats"])
        else:
            self.stats = StatsConfig()
            
        if "stats" not in self.config:
            self.config["stats"] = self.stats.config

        
class DataSeriesConfig(Config):
    """A Config object for a DataSeries."""

    CONFIG_NAME = "series"

    def __init__(self, config: dict, logger_config: LoggerConfig = None, stats_config: StatsConfig = None):
        super().__init__(config)
        
        if len(self.config["nodes"]) > 0:
            if self.config["num_nodes"]:
                print('Warning: explicit node list overrides use of num_nodes and template_node.')
            if "logger" in self.config["nodes"][0]:
                self.nodes = [SensorNodeConfig(n) for n in self.config["nodes"]]
            else:
                self.nodes = [SensorNodeConfig(n, logger_config, stats_config) for n in self.config["nodes"]]
        
        else:
            self.nodes = [SensorNodeConfig(self.config["template_node"], logger_config, stats_config) for _ in range(self.config["num_nodes"])]
            for i, n in enumerate(self.nodes):
                n.config["node_id"] = i

    def get_flattened_config(self):
        return {
            "key": self.config["key"],
            "nodes": [n.get_flattened_config() for n in self.nodes]
        }

class ExperimentConfig(Config):
    """A Config object for an Experiment."""

    CONFIG_NAME = "experiment"
    
    def __init__(self, config: dict, logger_config: LoggerConfig = None, stats_config: StatsConfig = None):
        super().__init__(config)
        self.energy_model: EnergyModelConfig = EnergyModelConfig(self.config["energy_model"])
        self.logger: LoggerConfig = logger_config
        self.stats: StatsConfig = stats_config
        self.series = [DataSeriesConfig(s, logger_config, stats_config) for s in self.config["series"]]

        series_key_set = set([s.config["key"] for s in self.series])
        if len(series_key_set) != len(self.series):
            print(f'Warning: non-unique series keys detected ({series_key_set} vs {[s.config["key"] for s in self.series]})! Results may be overwritten!')

    def get_flattened_config(self):
        return {
            "num_trials": self.config["num_trials"],
            "max_time": self.config["max_time"],
            "max_packets": self.config["max_packets"],
            "energy_model": self.energy_model.get_flattened_config(),
            "series": [s.get_flattened_config() for s in self.series]
        }

class LureConfig(Config):
    """A Config object for a top-level Lure object."""

    def __init__(self, config_dir: str, top_config_file: str):
        super().__init__(file=f'{config_dir}/{top_config_file}')
        Config.CONFIG_DIR = config_dir
        if "stats" in self.config:
            stats = StatsConfig(self.config["stats"])
        else:
            stats = None
        if "logger" in self.config:
            logger = LoggerConfig(self.config["logger"])
        else:
            logger = None
        self.experiments = [ExperimentConfig(e, logger, stats) for e in self.config["experiments"]]
    
    def get_flattened_config(self):
        return {
            "num_procs": self.config["num_procs"],
            "experiments": [e.get_flattened_config() for e in self.experiments] 
        }

    def to_file(self, file: str):
        with open(file, 'w') as f:
            json.dump(self.get_flattened_config(), f, indent=4)

class PlotterConfig(Config):
    """A Config object for a Plotter."""

    def __init__(self, config_dir: str = 'config'):
        super().__init__(file=f'{config_dir}/plot.json')

        try:
            self.title : str = self.config["title"]
            self.plot_upper_bounds : int = self.config["plot_upper_bounds"]
            self.plot_bound_intersection_vert : int = self.config["plot_bound_intersection_vert"]
            self.xlabel : str = self.config["xlabel"]
            self.series: Dict[str, str] = self.config["series"]
        except KeyError:
            print('No plot config found. Using defaults.')
            self.series = None