from lure.config.configuration import Config
from lure.node.net.ill.basic_ill import BasicILL
from lure.node.net.ill.ill import ILLConfigKey
from lure.node.net.packet import Packet
from lure.node.lmp.lmp import LMPConfigKey
from lure.node.stats import Stats, StatsProvider

class GILL(BasicILL):
    """A Good-enough ILL that dynamically reconfigures the LMP based on whether the node is a sender or receiver.
    """

    def __init__(self, config: Config):
        super().__init__(config)
        self.receiver_on_slots = None
        self.sender_on_slots = None
        config.extract("receiver_on_slots", self, 20)
        config.extract("sender_on_slots", self, 2)

    def set_config(self, key: ILLConfigKey, value) -> bool:
        """Set a configuration value identified by key

        :param key: Value to determine ILL configuration
        :type key: ILLConfigKey
        :param value: Value attached to the configuration
        :type value: any
        :return: Sucessfully set the requested simulation
        :rtype: bool
        """
        if key is ILLConfigKey.SENDER_ON_SLOTS:
            try:
                self.sender_on_slots = int(value)
                return True
            except ValueError as e:
                return False
        elif key is ILLConfigKey.RECEIVER_ON_SLOTS:
            try:
                self.receiver_on_slots = int(value)
                return True
            except ValueError as e:
                return False
        else:
            return super().set_config(key, value)

    def get_config(self, key: int):
        """Get a configuration value identified by key


        :param key: Selects the ILL configuration
        :type key: int
        :return: Value of the configuration
        :rtype: any
        """
        if key is ILLConfigKey.SENDER_ON_SLOTS:
            return self.sender_on_slots
        elif key is ILLConfigKey.RECEIVER_ON_SLOTS:
            return self.receiver_on_slots
        else:
            return super().get_config(key)
        
    def boot(self):
        """Called on node boot. Decides whether to boot as a receiver or sender depending on whether the sender queue is empty
        """
        super().boot()
        if self.send_queue.queues_empty():
            self.lmp.set_config(LMPConfigKey.ON_TIME_MS, self.receiver_on_slots * self.netstack.slot_length)
            self.stats.increment("ill_boot_as_receiver")
            self.debug(f'entered receive mode on boot')
        else:
            self.lmp.set_config(LMPConfigKey.ON_TIME_MS, self.sender_on_slots * self.netstack.slot_length)
            self.stats.increment("ill_boot_as_sender")
            self.debug(f'entered sender mode on boot')
    
    def send_packet(self, packet: Packet, booting: bool=False) -> bool:
        """Called by the network layer to queue a packet

        :param packet: The packet to be queued
        :type packet: Packet
        :param booting: Whether this method was called while the node was booting, defaults to False
        :type booting: bool, optional
        :return: True if the packet was passed to the MAC immediately, else False
        :rtype: bool
        """
        ret = super().send_packet(packet, booting)
        if ret:
            self.lmp.set_config(LMPConfigKey.ON_TIME_MS, self.sender_on_slots * self.netstack.slot_length)
            self.stats.increment("ill_switch_to_sender")
            self.debug(f'node:, ill: find mac successfully start sending. Set LMP to sender on-time in send_packet function')
            self.debug(f'entered sender mode (send_packet)')

        return ret
            
    def packet_sent(self, packet: Packet, success: bool):
        """Called by MAC after packet is sent. Switches the ILL to receiver mode if the send queue is now empty

        :param packet: The packet sent
        :type packet: Packet
        :param success: True, if the packet was successfully sent
        :type success: bool
        """
        super().packet_sent(packet, success)
        if self.send_queue.queues_empty():
            # config LMP to stay on for an additional receiver on-time
            self.lmp.set_config(LMPConfigKey.ON_TIME_MS, self.receiver_on_slots * self.netstack.slot_length + self.time_module.clock())
            self.stats.increment("ill_switch_to_receiver")
            self.debug(f'entered receive mode, queue empty')

    def __str__(self):
        return f'GILL-rxslots-{self.receiver_on_slots}_txslots-{self.sender_on_slots}'

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        # TODO: can you call the superclass setter?
        self._stats = stats
        self.send_queue.stats = stats

        stats.register("ill_boot_as_sender", 0)
        stats.register("ill_boot_as_receiver", 0)
        stats.register("ill_switch_to_sender", 0)
        stats.register("ill_switch_to_receiver", 0)
            
