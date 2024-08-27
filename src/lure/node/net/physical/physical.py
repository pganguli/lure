from enum import Enum
from typing import TYPE_CHECKING, Tuple, Callable, List
import simpy 

from lure.node.stats import Stats, StatType, StatsProvider
from lure.lure_logger import Loggable
from lure.config.configuration import Config
from lure.node.net.packet import Packet
from lure.node.net import Netstack
from lure.node.sensor_node import SensorNode

class PhysicalConfigKey(Enum):
    pass

class Physical(StatsProvider, Loggable):
    """Manages the physical layer for the netstack
    """

    def __init__(self, config: Config):
        self.neighbor_list: List[int] = []
        self.netstack: Netstack = None
        self.all_netstacks = None
        self.node_id = None
        self.receive_cb = None
        self.sent_cb = None
        self.use_promiscuous_mode = None
        config.extract("use_promiscuous_mode", self, True)
    
    def initialize(self, node: SensorNode, list_of_netstacks: List['Netstack']):
        """Initialize with the simulation

        :param node: The node this layer belongs to
        :type node: SensorNode
        :param list_of_netstacks: All netstacks participating in the simulation
        :type list_of_netstacks: List[&#39;Netstack&#39;]
        """
        self.netstack = node.netstack
        self.node_id = node.node_id
        self.all_netstacks = list_of_netstacks     

    def register_receive_cb(self, callback: Callable[[Packet], None]):
        """Register the callback function for packet reception

        :param callback: Callback function for the MAC layer
        :type callback: Callable[[Packet], None]
        """     
        self.receive_cb = callback
    
    def register_sent_cb(self, callback: Callable[[Packet], None]):
        """Register the callback function for packet transmission

        :param callback: Callback function for the MAC layer
        :type callback: Callable[[Packet], None]
        """
        self.sent_cb = callback
    
    def get_neighbor_by_id(self, id: int) -> Netstack:
        """Retrieve the netstack who's address matches the id paramter

        :param id: ID of the desired node 
        :type id: int
        :return: The desired netstack
        :rtype: Netstack
        """
        try:
            if id in self.neighbor_list:
                return [n for n in self.all_netstacks if n.addr == id][0]
        except IndexError:
            return None
    
    def get_neighbors(self) -> List[int]:
        """Retrives all physical neighbors

        :return: A list of all the physical neighbors of this node
        :rtype: List[int]
        """
        return self.neighbor_list

    def start_receive_on_neighbor(self, neighbor_id: int) -> bool:
        """Checks availability of a neighbor to begin transmission. Calls methods to start reception

        :param neighbor_id: The desired ID to send to
        :type neighbor_id: int
        :return: True if transmission was able to start
        :rtype: bool
        """
        if neighbor_id == self.netstack.BROADCAST_ADDRESS or self.use_promiscuous_mode:
            self.debug(f"Attempting broadcast to {self.neighbor_list}")
            known_nodes = [self.get_neighbor_by_id(n) for n in self.neighbor_list]
        else:
            known_nodes = [self.get_neighbor_by_id(neighbor_id)]
        success = False
        for node in known_nodes:
            if node is not None:
                # Logic to prevent the Hidden Node phenomenon. If the destination node...
                # ...does not have neighbors transmitting, start receive on it
                if not node.physical.neighbor_is_transmitting():
                    success |= node.mac.start_receive()
                    self.debug(f"Started receive on node{node.addr}, from node{self.netstack.addr}")
                # ...has neighbors transmitting, cancel all reception on that node due to interference
                else:
                    node.mac.cancel_reception()
                    self.debug(f"Cancelled all reception on node{node.addr} from node{self.netstack.addr}, because of interference from multiple nodes ")
                    # "success |= False" symbolically shows that sending to this node was a failure
        return success

    def packet_received_on_neighbor(self, neighbor_id: int, packet: Packet, transmitter_id: int) -> bool:
        """Called when a packet is done transmitting and it waits to see of the transmission was successful

        :param neighbor_id: Receiver of the packet
        :type neighbor_id: int
        :param packet: The packet sent
        :type packet: Packet
        :param transmitter_id: The id of the transmitter (this node)
        :type transmitter_id: int
        :return: True if the other node successfully received the packet
        :rtype: bool
        """
        if neighbor_id == self.netstack.BROADCAST_ADDRESS or self.use_promiscuous_mode:
            known_nodes = [self.get_neighbor_by_id(n) for n in self.neighbor_list]
        else:
            known_nodes = [self.get_neighbor_by_id(neighbor_id)]
        success = False
        for node in known_nodes:
            packet_copy = Packet.from_packet(packet=packet)
            if node is not None:
                success |= node.mac.packet_received(packet_copy, transmitter_id)
        return success

    def get_ack_from_neighbor(self, neighbor_id: int) -> Packet:
        """Calls the neighbor to provide an ACK packet to this node

        :param neighbor_id: The id of the node that should supply an ACK 
        :type neighbor_id: int
        :return: The ACK packet
        :rtype: Packet
        """
        if neighbor_id == self.netstack.BROADCAST_ADDRESS:
            known_nodes = [self.get_neighbor_by_id(n) for n in self.neighbor_list]
        else:
            known_nodes = [self.get_neighbor_by_id(neighbor_id)]
        for node in known_nodes:
            if node is not None:
                ack = node.mac.send_ack()
                # TODO: collisions between acks from multiple receivers?
                if ack:
                    return ack
        return None

    def cancel_reception_on_neighbors(self):
        """Cancel reception of packets for all neighbors
        """
        #TODO: Does this ever cause packets to stop receiving when this node isn't involved
        for node in [self.get_neighbor_by_id(n) for n in self.neighbor_list]:
            node.mac.cancel_reception()

 

    def neighbor_is_transmitting(self) -> bool:
        """Checks if any neighbor is currently transmitting

        :return: True if any physical neighbor is currently transmitting
        :rtype: bool
        """
        for n in self.neighbor_list:
            if self.get_neighbor_by_id(n).mac.is_transmitting:
                return True
        return False

    def boot(self):
        pass
    # ========== Unused Currently ==========

    def set_config(self, key: PhysicalConfigKey, value) -> bool:
        pass
    
    def get_config(self, key: PhysicalConfigKey):
        pass

    # def send_packet(self, destination_id: int, payload: str, callback: Callable[[int, bool], None]) -> bool:
    #     pass

    # def packet_sent(self, packet: Packet, success: bool):
        pass
        
    def packet_received(self, packet: Packet, sender_id: int):
        pass 

    def execute(self):
        pass 


    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats