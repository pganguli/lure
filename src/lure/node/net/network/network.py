from enum import Enum
from typing import TYPE_CHECKING
from typing import Callable
import simpy 

from lure.node.stats import Stats, StatType, StatsProvider
from lure.lure_logger import Loggable
from lure.config.configuration import Config
from lure.node.net.packet import Packet
from lure.node.net import Netstack
from lure.node.sensor_node import SensorNode

class Network(StatsProvider, Loggable):
    """Controls the basic functionality of the network layer and how it interfaces with other protocols
    """
    
    def __init__(self, config: Config):
        self.next_seqno = 0
        self.netstack: Netstack = None
        self.node_id = None
        self.application_receive_cb = None
        self.application_sent_cb = None
        self.routes = {}
    
    def initialize(self, node: SensorNode, simpy_env: simpy.core.Environment):
        """Initializes the node's network protocol object with the simulation environment

        :param node: The SensorNode object that is this class belongs to
        :type node: SensorNode
        :param simpy_env: The simpy environment of the simulation. It is invoked in this class for time tracking purposes
        :type simpy_env: simpy.core.Environment
        """
        self.netstack = node.netstack
        self.node_id = node.node_id
        self.simpy_env = simpy_env 
    
    def boot(self):
        """Logs that the Network is active on boot
        """
        self.debug(f'booting ')
    
    def send_packet(self, destination_id: int, payload: str):
        """Create the packet and pass it to ILL.send_packet(). Embeds this node's ID into the packet as the source. Determine next hop and embed into the packet as the receiver

        :param destination_id: The packet's destination node's ID
        :type destination_id: int
        :param payload: The payload of the packet
        :type payload: str
        """
        pkt = Packet(seqno=self.next_seqno, source_id=self.netstack.addr, destination_id=destination_id, payload=payload, slot_length=self.netstack.slot_length, ack_fraction=self.netstack.mac.ack_fraction, gen_time=self.simpy_env.now)
        self.debug(f'Packet created. Dest={destination_id}')
        self.stats.list_append(StatType.PACKETS_GENERATED_DESTINATIONS, destination_id)
        self.next_seqno += 1
        pkt.next_hop = self.get_next_hop(pkt)
        self.netstack.ill.send_packet(pkt)
        self.debug(f'Packet passed to ILL. dest={pkt.destination_id}, next_hop: {pkt.next_hop}')

    
    def packet_sent(self, packet: Packet, success: bool):
        """A part of the sent outcome chain. Called by ILL.sent_packet(). Calls the corresponding app layer callback in SensorNode.

        :param packet: The successfully sent packet's information
        :type packet: Packet
        :param success: True if successfully sent. False if an error was encountered.
        :type success: bool
        """
        self.debug("Packet sent from network")
        if(packet.source_id == self.node_id):
            self.application_sent_cb(packet=packet, status=success)
        
    def packet_received(self, packet: Packet, sender_id: int):
        """The network protocol response to receiving a packet.
            Calls the corresponding app layer callback only when this node is the destination for this packet
            OR
            When a next hop is needed for a destination, assign the new next hop to the packet
            OR
            Discards broadcast packets

        :param packet: The packet received
        :type packet: Packet
        :param sender_id: The node_id that the packet comes from
        :type sender_id: int
        """
        self.stats.increment(StatType.PACKETS_RECEIVED_NET)
        packet.net_record["hop_record"].append((self.node_id, self.simpy_env.now))
        if(packet.destination_id == self.node_id):
            self.debug(f'Packet {packet} has arrived at its destination')
            packet.net_record["arrive_time"] = self.simpy_env.now
            self.stats.time_series_append(StatType.NETWORK_PACKET_TRAILS, packet.net_record)
            self.application_receive_cb(packet, sender_id)
        else:
            if (packet.destination_id == None) and (packet.next_hop == self.netstack.BROADCAST_ADDRESS):
                self.debug("Broadcast packet received")
                self.stats.time_series_append(StatType.NETWORK_BROADCASTS, (sender_id, self.netstack.physical.get_neighbor_by_id(sender_id).physical.get_neighbors()))
                self.application_receive_cb(packet, sender_id)
            else:
                self.debug(f'Not this packet\'s destination. Next hop is {packet.next_hop}')
                packet.next_hop = self.get_next_hop(packet)
                self.netstack.ill.packet_forward(packet)

    def register_receive_cb(self, callback: Callable[[Packet], None]):
        """Registers the packet reception callback function for the previous netstack layer. Passes the network's packet receive callback to ILL.

        :param callback: Application layer receive packet callback 
        :type callback: Callable[[Packet], None]
        """
        self.application_receive_cb = callback
        self.netstack.ill.register_receive_cb(self.packet_received)
    
    def register_sent_cb(self, callback: Callable[[Packet], None]):
        """Registers the packet sent callback function for the previous netstack layer. Passes the network's packet sent callback to ILL.

        :param callback: Application layer packet sent callback
        :type callback: Callable[[Packet], None]
        """
        self.application_sent_cb = callback
        self.netstack.ill.register_sent_cb(self.packet_sent)

    def get_next_hop(self, packet: Packet) -> int:
        """Returns the node_id of the next_hop destination for the packet. The next hop is determined by a subclass and this function checks the packet parameter's viability.

        :param packet: The packet looking for its next hop address
        :type packet: Packet
        :raises ValueError: Raises a value error if the packet parameter has no destination_id
        :return: The id of the next hop node
        :rtype: int
        """
        if packet.destination_id == None:
            raise ValueError("Packet submitted to network.get_next_hop() must have a destination_id")
        else:
            return None

    def execute(self):
        """What executes on every tick of the simulation. (Currently no purpose)
        """
        pass

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.stats.register_time_series(StatType.NETWORK_PACKET_TRAILS)
        self.stats.register(StatType.PACKETS_RECEIVED_NET)
        self.stats.register(StatType.PACKETS_GENERATED_DESTINATIONS)
        self.stats.register_list(StatType.NETWORK_NEIGHBORS)
        self.stats.register_time_series(StatType.NETWORK_BROADCASTS)
