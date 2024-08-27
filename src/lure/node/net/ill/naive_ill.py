from lure.node.net.ill.ill import ILL
from lure.node.stats import StatType

class NaiveILL(ILL):
    """An ILL that queues in volatile RAM
    """

    def boot(self):
        """Called on node boot. Record an "infinite" delay if the MAC was attempting to send a packet when the node shut off
        """
        if not self.send_queue.queues_empty():
            self.stats.time_series_append(StatType.PACKET_QUEUE_EVENTS, -999999999)
        self.send_queue.clear_all()
        super().boot()

    def __str__(self):
        return 'NaiveILL'

