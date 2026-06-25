from enum import Enum
from lure.config.configuration import Config
from lure.lure_logger import Loggable
from lure.node.lmp.lmp import LMP
from lure.node.net.netstack import Netstack
from lure.node.net.packet import Framer, Packet, PacketType

from typing import Callable

from lure.node.net.queue import PacketQueue
from lure.node.sensor_node import SensorNode
from lure.node.stats import StatType, Stats, StatsProvider


class ILLConfigKey(Enum):
    """Configuration for the ILL"""

    SENDER_ON_SLOTS = 1
    RECEIVER_ON_SLOTS = 2
    RECEIVE_TIMEOUT_MS = 3


# An ILL that queues in nonvolatile memory, but does not interact with the LMP.
class ILL(Framer, Loggable, StatsProvider):
    """An ILL that queues packets in nonvaltile memory. Inherits Framer, Loggable, and StatsProvider."""

    def __init__(self, config: Config):
        self.send_queue = PacketQueue(
            max_total_size=config.config["max_total_queue_size"]
        )
        self.lmp: LMP = None
        self.netstack: Netstack = None

        self.network_receive_cb = None
        self.network_sent_cb = None

        self.handshake = False

    def initialize(self, node: "SensorNode"):
        """Initializes with the simulation. Establishes a reference to its parent lmp and netstack.

        :param node: The parent node of this protocol
        :type node: SensorNode
        """
        self.lmp = node.lmp
        self.netstack = node.netstack

    def set_config(self, key: ILLConfigKey, value) -> bool:
        """Sets a configuration value identified by key. To be implemented by subclasses."""
        pass

    def get_config(self, key: int):
        """Get a configuration value identified by key. To be implemented by subclasses"""
        pass

    def boot(self):
        """Called on boot. Tries to send a packet to one of its neighbors

        :return: Success status of packet send
        :rtype: bool
        """
        self.debug("booting ")
        return self.send_packet(packet=None, booting=True)

    def send_packet(self, packet: Packet, booting: bool = False) -> bool:
        """Selects a packet to pass to the MAC layer for further sending. Called by :py:class:`lure.node.net.network.Network`.

        :param packet: Packet to be sent. CONTROL packets send this packet directly. DATA packets are queued and the oldest packet of the same receiver type.
        :type packet: Packet
        :param booting: Whether this packet was called on BOOT, defaults to False
        :type booting: bool, optional
        :raises Exception: Must specify a packet (unless this method is called on boot)
        :return: True if the packet is handed to the MAC layer immediately. Else, it is False.
        :rtype: bool
        """

        # Handles sending a control packet
        if (packet is not None) and (packet.type == PacketType.CONTROL):
            if self.netstack.frame(packet):
                self.debug("Control packet sent")
                self.netstack.mac.send_packet(self.netstack.BROADCAST_ADDRESS, packet)
            return None

        if self.send_queue.queues_empty():
            # For the first packet in the queue, we cancel pending outgoing packets at the MAC because they must be control packets
            self.netstack.mac.abort_send()
            if booting:
                self.handshake = False
                return False

        if booting:
            self.debug("packets in queue")
            receiver_id = self.send_queue.find_non_empty_receiver()
            if receiver_id is None:
                self.debug("No packets to send")
            else:
                self.debug(f"Packets found for node {receiver_id}")
        elif packet is not None:
            receiver_id = packet.next_hop
            if self.send_queue.queue_packet(packet, receiver_id):
                self.debug(f"Queued packet {packet}")
            else:
                self.debug("Failed to queue packet (Queue is full)")
                self.stats.increment(StatType.PACKETS_DROPPED_ILL)
                self.network_sent_cb(packet, False)
                # TODO: Should we be returning false here? Do we still want to send a packet even if a new one cannot be added?
                return False
        else:
            raise Exception(
                f"ILL.send_packet() the packet parameter must be specified unlesss this method is called on BOOT. booting={booting}, packet={packet}"
            )

        # Pick the oldest packet in queue (of this next_hop) to send.
        packet_to_send = self.send_queue.next_packet(receiver_id)
        if packet_to_send is None:
            self.debug("packet_to_send is None")

        self.netstack.frame(packet_to_send)
        self.debug(f"Framed packet {packet_to_send}")

        if receiver_id != packet_to_send.next_hop:
            raise ValueError(
                f"Node {self.netstack.addr}: receiver_id {receiver_id} should match queued packet's next_hop: {packet_to_send.next_hop}. Packet {packet_to_send} info = type: {packet_to_send.type}, source: {packet_to_send.source_id}, dest: {packet_to_send.destination_id}, queue_keys: {self.send_queue.packet_queue.keys()}"
            )

        # MAC will reject the send call if it's already sending a packet
        if self.netstack.mac.send_packet(receiver_id, packet_to_send):
            self.debug("Find mac, successfully start sending.")
            return True

    def packet_sent(self, packet: Packet, success: bool):
        """Callback function that handles a packet after being sent. Called by MAC after packet is sent.

        :param packet: Packet that was sent
        :type packet: Packet
        :param success: Whether the packet was sent successfully
        :type success: bool
        """
        self.debug(f"Packet sent, success: {success}")
        receiver_id = packet.next_hop

        if success:
            self.stats.increment(StatType.PACKETS_SENT_ILL)
            if not self.handshake:
                self.handshake = True
                self.stats.time_series_append(StatType.ILL_HANDSHAKE, None)

            if not self.send_queue.remove_packet(receiver_id, packet.seqno):
                self.debug("packet_sent called for packet that is no longer in queue")

            # check whether there are remaining packets to send to this current receiver
            if not self.send_queue.queue_empty(receiver_id):
                next_packet = self.send_queue.next_packet(receiver_id)
                self.netstack.mac.send_packet(receiver_id, next_packet)

            # check whether there are other receivers whose has packets remaining
            elif not self.send_queue.queues_empty():
                self.debug(f"packet_sent is called, done sending to {receiver_id}")
                next_receiver_id = self.send_queue.find_non_empty_receiver()
                next_packet = self.send_queue.next_packet(next_receiver_id)
                self.netstack.mac.send_packet(next_receiver_id, next_packet)

            else:
                pass

        # Packet was not successfully sent by MAC
        else:
            # TODO: what to do on mac failure?
            self.debug(f"Warning: MAC failed to send packet {packet}")
            pass
        if packet.type is not PacketType.CONTROL:
            self.network_sent_cb(packet, success)

    def packet_received(self, packet: Packet, sender_id: int):
        """Called by MAC when a packet is received by the MAC layer.

        :param packet: Packet received by the MAC layer
        :type packet: Packet
        :param sender_id: The netstack address of the node who sent the packet
        :type sender_id: int
        """
        # TODO: Add a clause to add a packet that needs to be forwarded to THIS node's queue
        self.debug(f"Packet received from {sender_id}")
        if not self.handshake:
            self.handshake = True
            self.stats.time_series_append(StatType.ILL_HANDSHAKE, None)

        self.netstack.parse(packet)

        # if packet.type is not PacketType.CONTROL:
        #     self.network_receive_cb(packet, sender_id)
        if (
            packet.next_hop == self.netstack.addr
            or packet.next_hop == self.netstack.BROADCAST_ADDRESS
        ):
            self.network_receive_cb(packet, sender_id)

    def packet_forward(self, packet: Packet) -> bool:
        """Called by the network layer when a packet needs to be queued for forwarding.

        :param packet: Packet to be forwarded
        :type packet: Packet
        :return: Whether the packet was queued successfully or not
        :rtype: bool
        """
        receiver_id = packet.next_hop
        if self.send_queue.queue_packet(packet, receiver_id):
            self.debug(f"Queued packet {packet} for forwarding")
            return True
        else:
            self.debug("Failed to queue packet for forwarding (Queue is full)")
            self.stats.increment(StatType.PACKETS_DROPPED_ILL)
            return False

    def register_receive_cb(self, callback: Callable[[Packet, int], None]):
        """Registers callback method for receiving a packet from Network

        :param callback: Callback function
        :type callback: Callable[[Packet, int], None]
        """
        # Callback persists between on-times
        self.network_receive_cb = callback
        self.netstack.mac.register_receive_cb(self.packet_received)

    def register_sent_cb(self, callback: Callable[[Packet, int], None]):
        """Registers callback method for having sent a packet. Currently called by Network

        :param callback: Callback function
        :type callback: Callable[[Packet, int], None]
        """
        # Callback persists between on-times
        self.network_sent_cb = callback
        self.netstack.mac.register_sent_cb(self.packet_sent)

    def execute(self):
        """Called every execution cycle (i.e., every ms) and is generally used to allow timer emulation"""
        pass

    def __str__(self):
        return "ILL"

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.send_queue.stats = stats
        self.stats.register(StatType.PACKETS_SENT_ILL)
        self.stats.register(StatType.PACKETS_DROPPED_ILL)

    def frame(self, packet: Packet) -> bool:
        return False

    def parse(self, packet: Packet) -> bool:
        return False
