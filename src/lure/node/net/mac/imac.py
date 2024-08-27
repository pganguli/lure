from simpy.core import SimTime
from typing import TYPE_CHECKING, Callable
from lure.config.configuration import Config
from lure.node.stats import StatType
from lure.node.timestepper import Timestepper
if TYPE_CHECKING:
    from lure.node.sensor_node import SensorNode

from lure.node.net.mac.mac import MAC, MACConfigKey
from lure.node.net.packet import Packet, PacketType
from lure.node.time.time import TimeModule

class iMAC(MAC):
    """A baseline MAC protocol implementation
    """

    TIMER_KEY_BACKOFF = 'mac_backoff'
    TIMER_KEY_TRANSMIT = 'mac_transmit'
    TIMER_KEY_RECEIVE = 'mac_receive'

    def __init__(self, config: Config):
        super().__init__(config)

        self.backoff_slots = None
        # Determines how much of the slot is remaining when the receiver turns off its LMP.
        # Currently supported in range 1 <= ack_fraction * slot_length <= slot_length.
        self.ack_fraction = None
        config.extract("backoff_slots", self, 2)
        config.extract("ack_fraction", self, 0.4)

        self.current_packet = None
        self.current_receiver_id = None
        self.receive_cb = None
        self.sent_cb = None
        self.backoff_timeout = None
        self.backing_off = False
        self.transmit_timeout = 0

        self.waiting_for_ack = False
        self.ack_incoming = False
        self.packet_to_ack = None

        self.time_module: TimeModule = None
        self.timestepper: Timestepper = None

    def initialize(self, node: 'SensorNode'):
        """Initialize with the simulation

        :param node: This object's parent node
        :type node: SensorNode
        """
        super().initialize(node)
        self.time_module = node.time_module
        self.timestepper = node.timestepper

    def set_config(self, key: MACConfigKey, value) -> bool:
        """Set the configuration of this protocol

        :param key: The key to identify the desired configuration
        :type key: MACConfigKey
        :param value: The value the configuration should be set to
        :type value: any
        :return: True if the configuration was set successfully
        :rtype: bool
        """
        # TODO: add backoff timer value
        pass

    def get_config(self, key: int):
        """Get a configuration value identified by key

        :param key: The key to identify the desired configuration
        :type key: int
        """
        pass

    def boot(self):
        """Called on node boot
        """
        self.debug('booting')
        self.reset()
        if self.receive_cb is not None:
            self.is_listening = True
    
    def reset(self):
        """Called when the node boots and when the node dies. Resets the nodes current state and cancels current reception or transmission.
        """
        if self.is_transmitting:
            self.netstack.physical.cancel_reception_on_neighbors()
        self.is_sending = False
        self.is_transmitting = False
        self.is_receiving = False
        self.is_listening = False
        self.current_packet = None
        self.backing_off = False
        if self.packet_to_ack:
            self.debug('Dying while sending an ack')
            self.stats.increment(StatType.MAC_DEATHS_DURING_ACK)
        self.packet_to_ack = None
        self.waiting_for_ack = False
        if self.ack_incoming:
            self.debug('Dying while waiting on an ack')
            self.stats.increment(StatType.MAC_DEATHS_DURING_ACK)
        self.ack_incoming = False

    def send_packet(self, receiver_id: int, packet: Packet) -> bool:
        """Called by the ILL layer to prepare a packet for transmission

        :param receiver_id: The receiver of the packet
        :type receiver_id: int
        :param packet: The packet to be sent
        :type packet: Packet
        :return: True if not already in sending mode
        :rtype: bool
        """
        self.debug(f'Sending packet, is sending: {self.is_sending}, packet {packet}')
        if not self.is_sending:
            self.current_packet = packet
            self.debug(f"current_receiver_id set. Old = {self.current_receiver_id}, New = {receiver_id}")
            self.current_receiver_id = receiver_id
            self.is_sending = True
            # self.sent_cb = callback
            if not self.is_receiving and not self.backing_off:
                self._try_transmit()
            return True
        else:
            return False

    def packet_sent(self, status: bool):
        """Callback for when a packet is sent

        :param status: Status of packet transmission
        :type status: bool
        """

        self.debug(f'Packet sent, status: {status}')
        if status is True:
            self.is_sending = False
            # If we were previously listening, start listening again
            if self.receive_cb is not None:
                self.is_listening = True
            self.sent_cb(self.current_packet, True)
        else:
            # If the channel is occupied by another node, we back off and act as a receiver
            self.is_listening = True
            self.backoff_timeout = self.backoff_slots * self.netstack.slot_length
            self.debug(f'backoff time set to {self.backoff_timeout}')
            self.time_module.set_relative_timer(self.TIMER_KEY_BACKOFF, self.backoff_timeout)
            self.backing_off = True

    def start_receive(self) -> bool:
        """Called by the physical layer of the other node when this node beings to receive a packet

        :return: True if starting reception
        :rtype: bool
        """
        self.debug(f'Starting receive, is_listening {self.is_listening}, is_receiving {self.is_receiving}, is_transmitting {self.is_transmitting}')
        if self.is_listening and not self.is_receiving and not self.is_transmitting:
            self.is_receiving = True
            return True
        return False

    def packet_received(self, packet: Packet, sender_id: int) -> bool:
        """Callback for when a packet is received. 

        :param packet: Packet received
        :type packet: Packet
        :param sender_id: Node ID of the sender of the packet
        :type sender_id: int
        :return: False if the node did not successfully receive the packet
        :rtype: bool
        """
        if self.is_receiving and self.is_listening:
            self.debug(f'Packet received from {sender_id}')
            self.receive_cb(packet, sender_id)
            self.packet_to_ack = packet
            self.debug('backoff time set')
            self.backoff_timeout = self.netstack.slot_length + 1
            self.time_module.set_relative_timer(self.TIMER_KEY_BACKOFF, self.backoff_timeout)
            self.backing_off = True
            if packet.type is PacketType.DATA:
                self.stats.increment(StatType.MAC_DATA_RECEIVED)
            elif packet.type is PacketType.CONTROL:
                self.stats.increment(StatType.MAC_CONTROL_RECEIVED)
            return True
        else:
            self.debug(f'Packet dropped. Destination={packet.destination_id}, Sender={sender_id}')
            pass

        return False

    def send_ack(self) -> Packet:
        """Called by the physical layer

        :return: A packet with type ACK if successful. None otherwise 
        :rtype: Packet
        """
        if self.is_receiving and self.is_listening:
            if not self.packet_to_ack:
                self.debug(f'Expected to have a packet to ack but none found.')
                assert(False)
                return None
            ack = Packet(self.packet_to_ack.seqno, self.netstack.addr, self.packet_to_ack.source_id, packet_type=PacketType.ACK, slot_length=self.netstack.slot_length, ack_fraction=self.ack_fraction)
            self.netstack.frame(ack)
            self.debug(f'Sending ack!')
            self.is_receiving = False
            self.packet_to_ack = None
            return ack
        
        return None

    def cancel_reception(self):
        """Called by the other node if it stops transmitting unexpectedly (e.g., because it died)
        """
        #TODO: check that the tx being cancelled is the one we're actually receiving
        self.is_receiving = False

    def register_receive_cb(self, callback: Callable[[Packet, int], None]):
        """Registers the packet received callback method

        :param callback: The callback function that this layer reports back to
        :type callback: Callable[[Packet, int], None]
        """
        self.debug('register receive cb')
        if self.is_sending is False:
            self.is_listening = True
        self.receive_cb = callback
        self.netstack.physical.register_receive_cb(self.packet_received)
    
    def register_sent_cb(self, callback: Callable[[Packet, int], None]):
        """Registers the packet sent callback method

        :param callback: The callback function that this layer reports back to
        :type callback: Callable[[Packet, int], None]
        """
        self.debug('register sent cb')
        self.sent_cb = callback
        self.netstack.physical.register_sent_cb(self.packet_sent)

    def abort_send(self):
        """Aborts the current send and starts listening (if we have a receive callback)
        """
        #TODO: Is there a case when there won't be a receive_cb? Should there be one?
        self.is_transmitting = False
        self.is_sending = False
        self.current_packet = None
        if self.receive_cb is not None:
            self.is_listening = True

    def _try_transmit(self):
        """Attempt to transmit a packet 
        """
        self.is_listening = False
        self.waiting_for_ack = False
        # Only frame if the packet needs it (it may have been framed at the ILL)
        if not self.current_packet.framed:
            self.netstack.frame(self.current_packet)
        channel_occupied = self.netstack.physical.neighbor_is_transmitting() 
        if not self.is_transmitting and not channel_occupied:
            # Only gets to the receiver if it's listening
            self.debug(f'Starting receive on neighbor: {self.current_receiver_id}. Packet dest={self.current_packet.destination_id}, next_hop={self.current_packet.next_hop}')
            if self.netstack.physical.start_receive_on_neighbor(self.current_receiver_id): #TODO
                # receiver successfully start to receive
                self.debug(f'Starting transmission, receiver ({self.current_receiver_id}) is available!')
            else:
                self.debug(f'Starting transmission (receiver ({self.current_receiver_id}) not available)')

            self.is_transmitting = True
            
            #TODO: support packets of different lengths? For now this needs to be the same as the slot time.
            #self.transmit_timer = self.current_packet.get_transmit_time_ms()
            self.transmit_timeout = self.netstack.slot_length - self.netstack.slot_length * self.ack_fraction
            self.timestepper.set_relative_timer(self.TIMER_KEY_TRANSMIT, self.transmit_timeout)
        elif channel_occupied:
            self.debug('channel occupied, failed CCA')
            self.packet_sent(False)

    def execute(self):
        """Called every execution cycle and is generally used to allow timer emulation
        """
        if((self.current_packet is None) and self.is_sending):
            self.debug("Packet of NoneType in imac execute() while in sending mode")
        self.debug(f'execute')
        if self.backing_off:
            if self.time_module.timer_expired(self.TIMER_KEY_BACKOFF):
                self.backing_off = False
                self.debug('Backoff timer expired')
                self.packet_to_ack = None
                if self.is_sending:
                    self.debug('Returning to sending, turning off listening')
                    self.is_listening = False
                    self.is_receiving = False
                    self._try_transmit()

        elif self.is_sending and not self.is_transmitting and not self.is_receiving:
            # If we're sending but not transmitting, try starting a transmission
            self._try_transmit()
                
        if self.is_transmitting:
            if not self.waiting_for_ack and self.timestepper.timer_expired(self.TIMER_KEY_TRANSMIT):
                # Data packet is done transmitting
                if self.netstack.physical.packet_received_on_neighbor(self.current_receiver_id, self.current_packet, self.netstack.addr): #TODO:
                    self.debug('Finished transmission (success! waiting for ack...)')
                    self.ack_incoming = True
                else:
                    self.debug('Finished transmission (failure, waiting for ack anyway)')
                    self.ack_incoming = False
                ack_timeout = self.netstack.slot_length * self.ack_fraction
                self.timestepper.set_relative_timer(self.TIMER_KEY_TRANSMIT, ack_timeout)
                self.waiting_for_ack = True

            elif self.waiting_for_ack and self.timestepper.timer_expired(self.TIMER_KEY_TRANSMIT):
                # Done waiting for ack
                self.waiting_for_ack = False
                self.is_transmitting = False
                # Reset framed status so we get a fresh framing if we have to transmit this packet again
                self.current_packet.framed = False
                # Check if the reception was successful... simulation equivalent of the ack
                ack = self.netstack.physical.get_ack_from_neighbor(self.current_receiver_id) #TODO
                if ack:
                    if ack.seqno == self.current_packet.seqno and ((ack.source_id == self.current_packet.next_hop) or (ack.source_id == self.current_packet.destination_id) or (self.current_packet.next_hop == self.netstack.BROADCAST_ADDRESS)):
                        self.debug(f'Ack received')
                        self.stats.increment(StatType.MAC_ACKS_RECEIVED)
                        self.netstack.parse(ack)
                        self.is_sending = False
                        self.packet_sent(True)
                    else:
                        self.debug(f'Received an ack for the wrong packet! seqno(rx, expected): {ack.seqno},{self.current_packet.seqno}; ack source_id: {ack.source_id}; current packet(next hop, destination): {self.current_packet.next_hop},{self.current_packet.destination_id} ||| {self.netstack.physical.get_neighbors()}')
                else:
                    if self.ack_incoming:
                        self.debug(f'Expected ack not received, did the other node die?')
                    self.debug(f'No ack')
                    #self.is_listening = True
                self.ack_incoming = False
                if self.is_sending:
                    self._try_transmit()

    def __str__(self):
        return f'iMAC'
