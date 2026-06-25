from lure.config.configuration import Config
from lure.node.net.ill.ill import ILL, ILLConfigKey
from lure.node.net.packet import Packet, PacketType
from lure.node.sensor_node import SensorNode
from lure.node.time.time import TimeModule


class BasicILL(ILL):
    """An ILL that temporarily disables the LMP when succcessful communication occurs"""

    TIMER_KEY_RECEIVE = "ill_receive"
    TIMER_KEY_SEND = "ill_send"

    def __init__(self, config: Config):
        super().__init__(config)

        self.time_module: TimeModule = None

        self.receive_timeout = None
        self.receiving = False

        self.send_timeout = None
        self.sending = False

    def initialize(self, node: SensorNode):
        """Initialize with the simulation

        :param node: The node this object belongs to
        :type node: SensorNode
        """
        super().initialize(node)
        self.time_module = node.time_module
        self.receive_timeout = self.netstack.slot_length + 1
        self.send_timeout = self.netstack.slot_length + 1

    def set_config(self, key: ILLConfigKey, value) -> bool:
        """Set a configuration value identified by key

        :param key: A key used to select the configuration
        :type key: ILLConfigKey
        :param value: The value the configuration will be set to
        :type value: _type_
        :return: True if :py:const:`lure.node.net.ill.ill.ILLConfigKey.RECEIVE_TIMEOUT_MS` was set successfully
        :rtype: bool
        """
        if key is ILLConfigKey.RECEIVE_TIMEOUT_MS:
            try:
                self.receive_timeout = int(value)
                return True
            except ValueError:
                return False

        return super().set_config(key, value)

    def get_config(self, key: int):
        """Get a configuration value identified by key

        :param key: A key used to select the configuration
        :type key: int
        :return: The configuration value
        :rtype: any
        """
        if key is ILLConfigKey.RECEIVE_TIMEOUT_MS:
            return self.receive_timeout

        return super().get_config(key)

    def boot(self):
        """Called on node boot. If no packets are in the sending queue, a control packet is sent."""
        super().boot()
        self.lmp.enable()
        self.debug("lmp enabled on boot")
        self.receiving = False
        self.sending = False

        if self.send_queue.queues_empty():
            self.debug("no packets in queue, trying a control packet")
            # Cheating on receiver ID
            packet = Packet(
                None,
                source_id=self.netstack.addr,
                destination_id=None,
                packet_type=PacketType.CONTROL,
                slot_length=self.netstack.slot_length,
                ack_fraction=self.netstack.mac.ack_fraction,
            )
            packet.next_hop = self.netstack.BROADCAST_ADDRESS
            self.send_packet(packet=packet, booting=True)

    def packet_sent(self, packet: Packet, success: bool):
        """Called by MAC after a packet is sent

        :param packet: The packet sent
        :type packet: Packet
        :param success: True if the packet was successfully sent
        :type success: bool
        """
        if success and packet.type == PacketType.CONTROL:
            self.debug("Control packet sent successfully")
            return

        super().packet_sent(packet, success)

        if success and not self.send_queue.queue_empty(packet.next_hop):
            self.lmp.disable()
            self._try_send()
            self.debug(
                f"disabled lmp: {self.send_queue.total_size()} pkts remaining in queue"
            )
        elif success:
            self.debug("no remaining packets for this receiver, switch to receive")
            self._try_receive()
            # self.lmp.enable()
            # if self.lmp.get_config(LMPConfigKey.ON_TIME_MS) is not None:
            #    self.lmp.set_config(LMPConfigKey.ON_TIME_MS, self.time_module.clock() + self.lmp.get_config(LMPConfigKey.ON_TIME_MS))
            # self.debug(f'enabled lmp, queue empty')

    def packet_received(self, packet: Packet, sender_id: int):
        """Called by MAC when a packet is received

        :param packet: Packet that was received
        :type packet: Packet
        :param sender_id: The node_id of the packet's sender
        :type sender_id: int
        """
        super().packet_received(packet, sender_id)
        self._try_receive()
        self.lmp.disable()  # Disable the LMP when a packet is received.
        self.debug("disabled lmp, pkt received")

    def execute(self):
        """Called every execution step. Primarily controls re-enabling the lmp"""
        if self.receiving and self.time_module.timer_expired(self.TIMER_KEY_RECEIVE):
            self.debug("rx time = 0, enable lmp")
            if self.send_queue.queues_empty():
                self.lmp.enable()
            else:
                self._try_send()
                # if self.lmp.get_config(LMPConfigKey.ON_TIME_MS) is not None:
                #   self.lmp.set_config(LMPConfigKey.ON_TIME_MS, self.time_module.clock() + self.lmp.get_config(LMPConfigKey.ON_TIME_MS))
            self.debug(
                f"enabled lmp, receive timer expired, {self.send_queue.total_size()} pkts remaining in queue"
            )
            self.receiving = False
        elif self.sending and self.time_module.timer_expired(self.TIMER_KEY_SEND):
            self.debug("Did not send another packet, reenabling LMP")
            self.sending = False
            self._try_receive()

    def _try_receive(self):
        """Sets receive mode to true and creates a receive timeout timer"""
        self.receiving = True
        self.time_module.set_relative_timer(
            self.TIMER_KEY_RECEIVE, self.receive_timeout
        )

    def _try_send(self):
        """Sets sending mode to true and creates a sender timeout timer"""
        self.sending = True
        self.time_module.set_relative_timer(self.TIMER_KEY_SEND, self.send_timeout)

    def __str__(self):
        return "BasicILL"
