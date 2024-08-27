from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Hashable, List, Tuple, Union

class PacketType(Enum):
    """The type assigned to a packet. Currently supports DATA, ACK, and CONTROL packets.
    """
    DATA = 0
    ACK = 1
    CONTROL = 2

class Packet:
    """Packet that gets sent during the simulation
    """

    def __init__(self, seqno: int, source_id: int, destination_id: int, payload='', packet_type: PacketType = PacketType.DATA, slot_length: int = None, ack_fraction: float = 0.2, gen_time: int = None):
        self.type = packet_type
        self.seqno = seqno
        self.source_id = source_id
        self.destination_id = destination_id
        self.payload = payload
        self.framed = False
        self.headers = dict()
        self.slot_length = slot_length
        self.ack_fraction = ack_fraction
        self.queue_arrive_time = None
        self.next_hop = None
        self.net_record: Dict[str, any] = dict()
        self.net_record["gen_time"] = gen_time
        self.net_record["source_node"] = source_id
        self.net_record["destination_node"] = destination_id
        self.net_record["hop_record"]: List[(any, int)] = list()
        self.net_record["hop_record"].append((source_id, gen_time))
        self.net_record["arrive_time"] = None
    
    @classmethod
    def from_packet(cls, packet):
        """A constructor that takes another packet as input to copy it

        :param packet: The packet to copy
        :type packet: Packet
        :return: A copy of the packet parameter
        :rtype: Packet
        """
        new_packet = cls(seqno=packet.seqno, source_id=packet.source_id, destination_id=packet.destination_id, payload=packet.payload, packet_type=packet.type, slot_length=packet.slot_length, ack_fraction=packet.ack_fraction, gen_time=packet.net_record["gen_time"])
        # Copy next_hop
        new_packet.next_hop = packet.next_hop
        # Copy hop record
        if len(packet.net_record["hop_record"]) > 1:
            for item in packet.net_record["hop_record"][1:]:
                new_packet.net_record["hop_record"].append(item)
        # Copy Headers
        old_header_keys = packet._get_header_keys()
        for key in old_header_keys:
            value, length = packet.headers[key]
            new_packet.set_header(key, value, length)
        return new_packet

    def set_header(self, key: Hashable, value: Any, length: int):
        """Sets a header of the packet

        :param key: Key value for the header
        :type key: Hashable
        :param value: Value for the header
        :type value: Any
        :param length: Header size length
        :type length: int
        """
        self.headers[key] = (value, length)

    def _get_header_keys(self) -> List[any]:
        """Getter for all header keys

        :rtype: List[any]
        """
        return list(self.headers.keys())

    def get_header(self, key: Hashable):
        """Getter for a header

        :param key: Key of the packet be retrieved
        :type key: Hashable
        :return: Header of the packet
        :rtype: any
        """
        try:
            return self.headers[key][0]
        except KeyError:
            return None

    def pop_header(self, key: Hashable):
        """Pops the specified header 

        :param key: Key value used to retrieve the correct header
        :type key: Hashable
        :return: Desired header
        :rtype: any
        """
        header = self.get_header(key)
        if header:
            del self.headers[key]
        return header

    def get_size(self) -> int:
        """Returns the size of a packet

        :return: Size
        :rtype: int
        """
        return len(self.payload) + sum([h[1] for h in self.headers.values()])

    def get_transmit_time_ms(self):
        """Returns the time to transmit in milliseconds

        :return: Time to transmit in milliseconds
        :rtype: int
        """
        # TODO: Transition this to rely on the size of the packet and physical characteristics

        if self.slot_length:
            if self.type is PacketType.DATA:
                return self.slot_length - self.slot_length * self.ack_fraction
            elif self.type is PacketType.ACK:
                return self.slot_length * self.ack_fraction
            else:
                return self.slot_length / 2
        return None

    def __str__(self):
        return f'[Packet from {self.source_id} to {self.destination_id}, seqno {self.seqno}, payload "{self.payload}"]'



class Framer(ABC):
    """An abstract class regulating framing and parsing packets
    """

    @abstractmethod
    def frame(self, packet: Packet) -> bool:
        return False

    @abstractmethod
    def parse(self, packet: Packet) -> bool:
        return False
