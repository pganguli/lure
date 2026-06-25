from enum import Enum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode
from lure.config.configuration import Config
from lure.lure_logger import Loggable
from lure.node.net.netstack import Netstack
from lure.node.net.packet import Packet

# from collections.abc import Callable
from typing import Callable

from lure.node.stats import StatType, Stats, StatsProvider


class MACConfigKey(Enum):
    """An enumerated type defining MAC configuration keys"""

    RETRIES = 1


class MAC(Loggable, StatsProvider):
    """The framework that all MAC protocols should base themselves upon"""

    def __init__(self, config: Config):
        self.netstack: Netstack = None
        self._is_sending = False
        self._is_transmitting = False
        self._is_listening = False
        self._is_receiving = False

    @property
    def is_sending(self) -> bool:
        """A property defining whether a node is in sending mode or not

        :return: True if the node is in sending mode
        :rtype: bool
        """
        return self._is_sending

    @is_sending.setter
    def is_sending(self, val: bool):
        if val != self._is_sending:
            self._is_sending = val
            self.stats.time_series_append(StatType.MAC_IS_SENDING, val)

    @property
    def is_transmitting(self) -> bool:
        """A property defining whether a node is in transmitting mode or not

        :return: True if the node is in transmitting mode
        :rtype: bool
        """
        return self._is_transmitting

    @is_transmitting.setter
    def is_transmitting(self, val: bool):
        if val != self._is_transmitting:
            self._is_transmitting = val
            self.stats.time_series_append(StatType.MAC_IS_TRANSMITTING, val)

    @property
    def is_listening(self) -> bool:
        """A property defining whether a node is in listening mode or not

        :return: True if the node is in listening mode
        :rtype: bool
        """
        return self._is_listening

    @is_listening.setter
    def is_listening(self, val: bool):
        if val != self._is_listening:
            self._is_listening = val
            self.stats.time_series_append(StatType.MAC_IS_LISTENING, val)

    @property
    def is_receiving(self) -> bool:
        """A property defining whether a node is in receiving mode or not

        :return: True if the node is in receiving mode
        :rtype: bool
        """
        return self._is_receiving

    @is_receiving.setter
    def is_receiving(self, val: bool):
        if val != self._is_receiving:
            self._is_receiving = val
            self.stats.time_series_append(StatType.MAC_IS_RECEIVING, val)

    def initialize(self, node: "SensorNode"):
        """Initialize with the simulation

        :param node: The node object this MAC layer belongs to
        :type node: SensorNode
        """
        self.netstack = node.netstack

    def set_config(self, key: MACConfigKey, value) -> bool:
        """Set a configuration value identified by key

        :param key: Key to the value being set
        :type key: MACConfigKey
        :param value: The value the configuration is being set to
        :type value: any
        :return: True if the configuration was set successfully
        :rtype: bool
        """
        pass

    def get_config(self, key: int):
        """Get a configuration value identified by key

        :param key: The key to the configuration being checked
        :type key: int
        """
        pass

    def boot(self):
        """Called on node boot"""
        pass

    def send_packet(self, receiver_id: int, packet: Packet) -> bool:
        """Called by an upper layer to prepare a packet for sending

        :param receiver_id: The receiver of the packet
        :type receiver_id: int
        :param packet: Packet to be sent
        :type packet: Packet
        :return: False if the MAC is currently sending, else True
        :rtype: bool
        """
        pass

    def start_receive(self) -> bool:
        """Called by the other node to start receiing an incoming packet"""
        pass

    def packet_received(self, packet: Packet, sender_id: int) -> bool:
        """Called by the other node when a packet should be received by this node.

        :param packet: Packet to be received
        :type packet: Packet
        :param sender_id: ID of the node who sent the packet
        :type sender_id: int
        :return: False if the node did not successfully receive the packet, else True
        :rtype: bool
        """
        pass

    def send_ack(self) -> Packet:
        """Called by the other node via its physical layer. Sends an ACK packet

        :return: Returns the packet with type ACK if successful, None otherwise
        :rtype: Packet
        """
        pass

    def cancel_reception(self) -> bool:
        """Called by other node if it stops transmitting unexpectedly, e.g. because it died"""
        self.is_receiving = False

    def register_sent_cb(self, callback: Callable[[Packet, int], None]):
        """Registers the callback function that the MAC layer will use it interface with the layer above it for packet sent events"""
        pass

    def register_receive_cb(self, callback: Callable[[Packet, int], None]):
        """Registers the callback function that the MAC layer will use it interface with the layer above it for receive events"""
        pass

    def abort_send(self):
        """Abort the current send, if any"""
        pass

    def execute(self):
        """Called every execution cycle, i.e. every ms, to allow timer evaluation"""
        pass

    def reset(self):
        """Called by SensorNode when the node dies"""
        pass

    def __str__(self):
        return "MAC"

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.stats.register_time_series(StatType.MAC_IS_RECEIVING)
        self.stats.register_time_series(StatType.MAC_IS_LISTENING)
        self.stats.register_time_series(StatType.MAC_IS_TRANSMITTING)
        self.stats.register_time_series(StatType.MAC_IS_SENDING)
