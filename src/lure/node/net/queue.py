# Packet queue structure
from lure.lure_logger import Loggable
from lure.node.net.packet import Packet
from typing import Optional

from lure.node.stats import StatType, Stats, StatsProvider


class PacketQueue(Loggable, StatsProvider):
    """A node's internal packet queue"""

    packet_queue = {}

    def __init__(self, max_total_size=100):
        self.packet_queue = {}

        # Added by Shen. queue_size: The total number of packets (to all receivers) the quene can store.
        self.max_total_size = max_total_size
        self.max_pkts_single_receiver = (
            max_total_size / 4
        )  # the maximum number of packets for a single receiver

    def total_size(self) -> int:
        """Returns the sum of the size of individual queues

        :return: The number of packets across each queue
        :rtype: int
        """
        return sum(len(q) for q in self.packet_queue.values())

    def queue_packet(self, packet: Packet, receiver_id: int) -> bool:
        """Queue a packet

        :param packet: The packet to be queued
        :type packet: Packet
        :param receiver_id: The ID of the node intended to receive the packet
        :type receiver_id: int
        :return: Success status of queuing the packet
        :rtype: bool
        """
        try:
            if len(self.packet_queue[receiver_id]) >= self.max_pkts_single_receiver:
                return False  # The queue is false
            else:
                self.packet_queue[receiver_id].append(
                    packet
                )  # Append to existing queue
                self.debug(f"after queue packet, packet queue: {self.packet_queue}")
        except KeyError:
            self.packet_queue[receiver_id] = [packet]  # Queue is created

        packet.queue_arrive_time = (
            self.stats.simpy_env.now
        )  # Used for PACKET_QUEUE_EVENTS
        self.stats.time_series_append(StatType.PACKETS_IN_QUEUE, self.total_size())
        return True

    def next_packet(self, receiver_id: int) -> Optional[Packet]:
        """Access the next packet to send to the specified receiver

        :param receiver_id: The ID of the node a packet is being sent to
        :type receiver_id: int
        :return: The packet for the destination. If the receiver does not exist or the queue is empty return None.
        :rtype: Optional[Packet]
        """
        try:
            return self.packet_queue[receiver_id][0]
        except KeyError:
            return None
        except IndexError:
            return None

    def deque_packet(self, receiver_id: int) -> Optional[Packet]:
        """Deque the packet for the next receiver after a successful send. Depreciated."""
        self.debug("deque packet")
        try:
            packet = self.packet_queue[receiver_id].pop(0)
            if len(self.packet_queue[receiver_id]) == 0:
                del self.packet_queue[receiver_id]
            self.stats.time_series_append(StatType.PACKETS_IN_QUEUE, self.total_size())
            return packet
        except KeyError:
            return None

    def remove_packet(self, receiver_id: int, seqno: int) -> bool:
        """Removes a packet from a queue based on its sequence number and intended receiver.

        :param receiver_id: The id of the node intended to receive this packet
        :type receiver_id: int
        :param seqno: The seqno of the packet to be removed
        :type seqno: int
        :return: Success status of removing the packet. False if the seqno or receiver queue does not exist.
        :rtype: bool
        """
        try:
            packet = [p for p in self.packet_queue[receiver_id] if p.seqno == seqno][0]
            self.packet_queue[receiver_id].remove(packet)
            self.stats.time_series_append(StatType.PACKETS_IN_QUEUE, self.total_size())
            self.stats.time_series_append(
                StatType.PACKET_QUEUE_EVENTS, packet.queue_arrive_time
            )
            if len(self.packet_queue[receiver_id]) == 0:
                del self.packet_queue[receiver_id]
            return True
        except KeyError:
            return False
        except IndexError:
            return False

    def queue_empty(self, receiver_id: int) -> bool:
        """Returns a boolean value indicating whether the specified queue is empty or not.

        :param receiver_id: Corresponds to a queue of packets intended to be sent to this node ID
        :type receiver_id: int
        :return: True if the queue is empty
        :rtype: bool
        """
        if receiver_id in self.packet_queue:
            self.debug(
                f"queue length for receiver {receiver_id}: {len(self.packet_queue[receiver_id])}"
            )
            return len(self.packet_queue[receiver_id]) == 0
        else:
            return True
        # return receiver_id not in self.packet_queue

    def queues_empty(self) -> bool:
        """Returns whether all of this node's queues are empty

        :return: True if all queues are empty
        :rtype: bool
        """
        for r in self.packet_queue:
            if len(self.packet_queue[r]) != 0:
                return False
        return True

    def find_non_empty_receiver(self):
        """Finds a non-empty queue for this node

        :return: The ID of the receiving node corresponding to the selected queue
        :rtype: int
        """
        if len(self.packet_queue) == 0:
            self.debug(
                "Warning: Fail to find a receiver due to empty queue. Return None!"
            )
            return None
        else:
            # TODO: This could use some reworking to better determine what packet is to be sent next
            for receiver_id in self.packet_queue:
                return receiver_id

    def clear(self, receiver_id: int):
        """Delete a queue

        :param receiver_id: ID of the queue to delete (corresponds to the node packets from that queue are sent to)
        :type receiver_id: int
        """
        del self.packet_queue[receiver_id]
        self.stats.time_series_append(StatType.PACKETS_IN_QUEUE, self.total_size())

    def clear_all(self):
        """Delete all queues belonging to this node"""
        receiver_ids = list(self.packet_queue.keys())
        for receiver_id in receiver_ids:
            self.clear(receiver_id)

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.stats.register_time_series(StatType.PACKETS_IN_QUEUE)
        self.stats.time_series_append(StatType.PACKETS_IN_QUEUE, 0)
        self.stats.register_time_series(StatType.PACKET_QUEUE_EVENTS)
