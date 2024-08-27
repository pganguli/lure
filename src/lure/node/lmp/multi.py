from typing import Any, Dict, TYPE_CHECKING
from lure.node.node_state import NodeState
if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode
from lure.config.configuration import Config
from lure.lure_logger import LogLevel, Loggable, LureLogger
from lure.node.lmp.lmp import LMP, LMPConfigKey
from lure.node.net.packet import Packet
from lure.node.stats import Stats, StatsProvider

class MultiLMP(LMP):
    """A LMP that can ve configured to contain multiple LMPs
    """

    def __init__(self, config: Config):
        super().__init__(config)
        self.lmps: Dict[str, LMP] = dict()
        self.current_lmp: LMP = None
        self.current_lmp_key = None

        try:
            for k, v in config.config["lmps"].items():
                self.lmps[k] = Config.instantiate_from_dict(v, 'lure.node.lmp')
                if not self.current_lmp:
                    self.current_lmp = self.lmps[k]
                    self.current_lmp_key = k
        except:
            print('Unable to parse MultiLMP configuration. Should contain a parameter "lmps" that is a dictionary of LMP dictionaries.')

    def initialize(self, node: 'SensorNode'):
        """Initialize with the simulation

        :param node: The node this LMP belongs to
        :type node: SensorNode
        """
        super().initialize(node)
        for lmp in self.lmps.values():
            lmp.initialize(node)

    def set_config(self, key: LMPConfigKey, value) -> bool:
        """Set a configuration value defined by a key

        :param key: Identified the desired configuration
        :type key: LMPConfigKey
        :param value: The value to set the configuration to
        :type value: any
        """
        if key is LMPConfigKey.CURRENT_LMP_KEY:
            try:
                self.current_lmp = self.lmps[value]
                self.current_lmp_key = value
            except KeyError:
                self.debug(f'LMP {value} not found in LMP dict.')
        else:
            self.current_lmp.set_config(key, value)

    def get_config(self, key: LMPConfigKey) -> Any:
        """Get a configuration value identified by key


        :param key: The key identifying the correct configuration
        :type key: LMPConfigKey
        :return: The value the configuration is set to
        :rtype: Any
        """
        if key is LMPConfigKey.CURRENT_LMP_KEY:
            return self.current_lmp_key
        return self.current_lmp.get_config(key)

    def boot(self):
        """Called on node boot
        """
        self.current_lmp.boot()

    def enable(self, lock: bool = False):
        """Enables the LMP (turns on early-die functionality)

        :param lock: If True the LMP becomes locked, defaults to False
        :type lock: bool, optional
        """
        self.current_lmp.enable(lock=lock)

    def disable(self):
        """Disables the LMP (early-die functionality)
        """
        self.current_lmp.disable()
        
    def execute(self) -> NodeState:
        """Called every execution cycle (1 ms)

        :return: True if the node should immediatley early-die, false otherwise
        :rtype: NodeState
        """
        return self.current_lmp.execute()

    def __str__(self):
        return 'MultiLMP'

    def register_log(self, logger: LureLogger, log_level: LogLevel, tag: str):
        """Overrides :py:meth:`lure.lure_logger.Loggable.register_log` for this object

        :param logger: The logger being registered
        :type logger: LureLogger
        :param log_level: The logging level
        :type log_level: LogLevel
        :param tag: The tag associated with this log
        :type tag: str
        """
        super().register_log(logger, log_level, tag)
        for lmp in self.lmps.values():
            lmp.register_log(logger, log_level, tag)

    def frame(self, packet: Packet) -> bool:
        """Frame the packet

        :param packet: The packet to be framed
        :type packet: Packet
        :return: The result of self.current_lmp.frame(packet)
        :rtype: bool
        """
        return self.current_lmp.frame(packet)

    def parse(self, packet: Packet) -> bool:
        """Parse the packet

        :param packet: Packet to be parsed
        :type packet: Packet
        :return: The result of self.current_lmp.frame(packet)
        :rtype: bool
        """
        return self.current_lmp.parse(packet)

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        for lmp in self.lmps.values():
            lmp.stats = stats