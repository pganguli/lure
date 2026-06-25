# LMP base class
from enum import Enum
from typing import Any, TYPE_CHECKING
from simpy.core import SimTime

from lure.node.node_state import NodeState

if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode
from lure.config.configuration import Config

from lure.lure_logger import Loggable
from lure.node.net.packet import Framer, Packet
from lure.node.stats import StatsProvider


class LMPConfigKey(Enum):
    OTHER = 0
    ON_TIME_MS = 1
    CURRENT_LMP_KEY = 2
    SLEEP_THRESHOLD = 3
    WAKE_THRESHOLD = 4


class LMP(Framer, Loggable, StatsProvider):
    """A Lifecycle Managment Protocol (LMP)"""

    def __init__(self, config: Config):
        self.enabled: bool = False
        self.locked: bool = False

    def initialize(self, node: "SensorNode"):
        """Initialize with the simulation

        :param node: The node this LMP belongs to
        :type node: SensorNode
        """
        pass

    def set_config(self, key: LMPConfigKey, value) -> bool:
        """Set a configuration value identified by a key

        :param key: The key to the LMP configuration
        :type key: LMPConfigKey
        :param value: The value to set the configuration to
        :type value: any
        :return: False
        :rtype: bool
        """
        return False

    def get_config(self, key: LMPConfigKey) -> Any:
        """Get a configuration vlaue identified by a key

        :param key: The key to the desired LMP configuration
        :type key: LMPConfigKey
        :return: The value of the configuration
        :rtype: Any
        """
        return None

    def boot(self):
        """Called on node boot. Enables LMP"""
        self.enable()
        self.locked = False

    def enable(self, lock: bool = False):
        """Enables the lmp (i.e., turns on early-die functionality)

        :param lock: Set to True if the LMP should be locked, defaults to False
        :type lock: bool, optional
        """
        self.debug("Enabled")
        self.enabled = True
        self.locked = lock

    def disable(self):
        """Disables the LMP if it is not locked"""
        if not self.locked:
            self.debug("Disabled")
            self.enabled = False

    def execute(self) -> NodeState:
        """Called every execution cycle (1 ms)

        :return: true if the node should (immediately) early-die, false otherwise
        :rtype: NodeState
        """
        return NodeState.OPERATING

    def get_time_til_wake(self) -> SimTime:
        """Retrieves the time until the next wakeup

        :return: Simulation time until next wakeup
        :rtype: SimTime
        """
        return None

    def get_time_til_sleep(self) -> SimTime:
        """Retrieves the time until the next sleep

        :return: Simulation time until next sleep
        :rtype: SimTime
        """
        return None

    def __str__(self):
        return "LMP"

    def frame(self, packet: Packet) -> bool:
        """Abstract method of Framer. Do nothing by default. Could call set_header() on the Packet.

        :param packet: Packet to frame
        :type packet: Packet
        :return: False
        :rtype: bool
        """
        # self.debug(f'Framing packet of type {packet.type}')
        return False

    def parse(self, packet: Packet) -> bool:
        """Abstract method of Framer. Do nothing by default. Could call pop_header() on the Packet.

        :param packet: Packet to parse
        :type packet: Packet
        :return: False
        :rtype: bool
        """
        # self.debug(f'Parsing packet of type {packet.type}')
        return False
