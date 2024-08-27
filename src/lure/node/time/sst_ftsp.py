from lure.config.configuration import Config
from lure.node.time.continuous_time import ContinuousTimeModule
from lure.node.net.packet import Packet, PacketType
from lure.node.stats import Stats, StatType, StatsProvider

from sklearn.linear_model import LinearRegression
from collections import deque
import numpy as np
from enum import Enum

class FTSPPacketKeys(Enum):
    TS_KEY = "timestamp"
    SEQ_NUM_KEY = "seq_num"
    ROOT_ID_KEY = "root_id"


class SSTFTSPTimeModule(ContinuousTimeModule):
    def __init__(self, config: Config):
        super().__init__(config)
        self.reg_table_size = None
        self.root_timeout = None
        self.sync_period = None
        self.dead_period_window = None
        self.max_ontimes_to_send_ts = None
        config.extract("reg_table_size", self, 10)
        config.extract("root_timeout", self, 100000)
        config.extract("sync_period", self, 30000)
        config.extract("dead_period_window", self, 5)
        config.extract("max_ontimes_to_send_ts", self, 5)
        self.est_shared_time = 0
        self.timestamp_received = False
        self.last_ts_time = 0
        self.time_to_sync = 0
        self.highest_seq_num = 1
        self.num_ontimes_since_last_ts = 0
        self.total_time_as_root = 0
        self.root_timeout_start = 0
        self.my_root_id = None
        # tables to track time
        self.ref_time = deque([], maxlen=self.reg_table_size) 
        self.loc_time = deque([], maxlen=self.reg_table_size)
  

    def time(self) -> int:
        """
        The function returns the best estimate of the reference time, which represents a continuous or
        shared sense of time.
        :return: the best guess of the reference time, which is represented as an integer.
        """
        return self.est_shared_time

    def boot(self, t: int):
        """
        This function updates the estimated shared time and checks for a root timeout.
        
        :param t: t is an integer parameter representing the current simulation time. It is used in the boot
        method to update the shared time estimate and check for root timeout
        :type t: int
        """
        super().boot(t)
        self.est_shared_time += self.last_pclk_est
        self.cont_local_time += self.last_pclk_est

        # increse number of on-time since last timestamp
        self.num_ontimes_since_last_ts += 1
        
        # Estimate reference time on each boot
        self.est_shared_time = self.est_ref_time_reg()

        self.stats.time_series_append(StatType.EST_SHARED_TIME, self.est_shared_time)
        self.stats.time_series_append(StatType.CONT_LCL_TIME, self.cont_local_time)
        # This code block is checking if the current node is not the root node and if last timestamp received time is greater than root timeout - Make current node the root node
        if (self.my_root_id != self.node_id and (self.est_shared_time - self.last_ts_time >= self.root_timeout)) or (self.my_root_id == None):
            self.my_root_id = self.node_id
            self.debug(f"Root timeout: Node {self.node_id} becomes root!")
            self.root_timeout_start = self.timestepper.simpy_env.now

    def execute(self):
        """
        The function updates the clock and appends the estimated shared time to a time series if the current
        time is a multiple of 10000.
        """
        if self._last_update is not None:
            executed_time = self.timestepper.simpy_env.now - self._last_update
            # Updates the clock for a given amount
            updated_clock = self.active_clock.update(executed_time)
            self.est_shared_time += updated_clock
            self.cont_local_time += updated_clock
        self._last_update = self.timestepper.simpy_env.now
        # Fetch estimated shared time of the node at Tm, if it's on
        if self.timestepper.simpy_env.now % 10000 == 0: 
            self.stats.time_series_append(StatType.EST_SHARED_TIME_TM, self.est_shared_time)
        
    def frame(self, packet: Packet) -> bool:
        """
        This function sends a packet with timestamp, sequence number, and root ID if certain conditions are met.        
        :param packet: The "packet" parameter is an instance of the "Packet" class, which is being passed as
        an argument to the "frame" method. The method is using this packet to set some header fields and
        send it to other nodes in the network
        :type packet: Packet
        :return: The function `frame` returns a boolean value. It returns `True` if the packet is needed to be sent, and `False` otherwise.
        """
        # Execute to update cont local and shared time
        self.execute()
        num_entries = len(self.ref_time)
        # Set packet headers
        packet.set_header(FTSPPacketKeys.TS_KEY, self.est_shared_time, 4)
        packet.set_header(FTSPPacketKeys.SEQ_NUM_KEY, self.highest_seq_num, 4)
        packet.set_header(FTSPPacketKeys.ROOT_ID_KEY, self.my_root_id, 4)
        # If I am the root node and There is time to send synchronization messages
        if(self.my_root_id == self.node_id):
            if((self.est_shared_time - self.time_to_sync) > self.sync_period):
                self.debug(f"Root Node {self.node_id} Sent Time Stamp {self.est_shared_time}")
                self.highest_seq_num += 1
                self.stats.increment(StatType.PACKETS_SENT_TIME)
                return True
            else:
                return False
        # if node is not a root node, send timestamps asynchronously
        # send timestamps only when node's regression tables are maxed out or if node is the root node and it is time to send
        elif((self.my_root_id != self.node_id) and (num_entries >= self.reg_table_size) and (self.num_ontimes_since_last_ts <= self.max_ontimes_to_send_ts)): #if a node is synchronized
            self.debug(f"Node {self.node_id} Sent Time Stamp {self.est_shared_time}")
            self.stats.increment(StatType.PACKETS_SENT_TIME)
            return True
        else:
            return False

    # Called for every incoming packet. Use this to pop headers out of the packet
    def parse(self, packet: Packet) -> bool:
        """
        This function parses a received packet and updates regression tables based on the contents of the packet.
        
        :param packet: The packet parameter is an instance of the Packet class, which contains information
        about the message being received, such as its headers and payload 
        :type packet: Packet
        :return: a boolean value. If the received timestamp is None, it returns False. If the message's root
        ID is less than the node's root ID, it updates the node's root ID and returns False. If the
        message's root ID is greater than the node's root ID or the message's sequence number is less than
        or equal to the node's highest sequence number, it returns False
        """ 
        # Execute to update cont local and shared time
        self.execute()
        msg_root_id = packet.pop_header(FTSPPacketKeys.ROOT_ID_KEY)
        msg_root_seq_num = packet.pop_header(FTSPPacketKeys.SEQ_NUM_KEY)
        received_ts = packet.pop_header(FTSPPacketKeys.TS_KEY)

        
        # In case node recieves a timestamp before it declares itself as root node
        if(self.my_root_id == None):
            self.my_root_id = self.node_id


        if received_ts == None or packet.type == PacketType.ACK: # if received an acknowledgement
            return False
        elif (msg_root_id < self.my_root_id):  # if received root id is less than my root id
            if (self.node_id == self.my_root_id): 
                self.debug(f"Node {self.node_id} removed as root")                
                self.total_time_as_root += self.timestepper.simpy_env.now - self.root_timeout_start
                self.stats.time_series_append(StatType.ROOT_TIMEOUT, [self.root_timeout_start, self.timestepper.simpy_env.now])
                self.stats.set(StatType.NODE_TOTAL_ROOT_TIMEOUT, self.total_time_as_root)
                self.stats.increment(StatType.PACKETS_RECEIVED_TIME)
            self.my_root_id = msg_root_id  
        elif msg_root_id > self.my_root_id or msg_root_seq_num <= self.highest_seq_num: # manages redundant information
            self.stats.increment(StatType.PACKETS_RECEIVED_TIME)
            return False      
        else:
            return False   

        # Update highest seq_num. It is used to manage redundant information that we get from the nodes
        self.highest_seq_num = msg_root_seq_num

        # Update time to synchronize
        if (self.est_shared_time >= self.time_to_sync+self.sync_period+5000):
            self.time_to_sync += self.sync_period
            self.debug(f"Time to sync period updated to {self.time_to_sync}")

        self.add_entry_and_estimate_drift(received_ts, packet)
        return True
    
    def add_entry_and_estimate_drift(self, received_ts, packet):
        """
        This function adds an entry to a time series stat object and updates local and reference time tables
        based on received time stamps.
        
        :param received_ts: The time stamp received from a packet sent by another node in the network
        :param packet: The "packet" parameter is an object that represents the data packet that was received
        by the node. It likely contains information such as the source ID of the transmitting node, the
        payload data, and any necessary metadata for the communication protocol being used
        """
        self.debug(f"Received TS: {received_ts} from node {packet.source_id}, shared time: {self.est_shared_time}, local time: {self.cont_local_time}")
        # Add packet transmit timeout to received time
        self.transmit_timeout = self.netstack.slot_length - self.netstack.slot_length * self.netstack.mac.ack_fraction
        received_ts += self.transmit_timeout
        # Estimate shared time
        self.execute()
        self.est_shared_time = self.est_ref_time_reg()
        # Update local/Reference time tables
        self.ref_time.append(received_ts)
        self.loc_time.append(self.cont_local_time)
        # append successful communication data to time series stat object
        self.stats.time_series_append(StatType.SUCC_COMM, [packet.source_id, self.node_id, received_ts, self.est_shared_time])
        self.stats.time_series_append(StatType.EST_SHARED_TIME, self.est_shared_time)
        # Update time stamp time
        self.last_ts_time = self.est_shared_time
        self.num_ontimes_since_last_ts = 0

    def get_ref_time_estimate(self, xdata, ydata, x):
        """
        This function uses linear regression to estimate a y-value for a given x-value based on a set of x
        and y data points.
        
        :param xdata: The x-coordinates of the data points used to fit the linear regression model
        :param ydata: The dependent variable data that we want to predict based on the independent variable
        xdata
        :param x: The value of x for which we want to estimate the corresponding y value
        :return: The function `get_ref_time_estimate` returns a single value, which is the predicted value
        of the linear regression model for the input `x`. This value represents the estimated reference time
        for the given input `x`.
        """
        xdata_reshape = np.reshape(xdata, (-1, 1))
        ydata = np.asarray(ydata, dtype=object)
        reg = LinearRegression().fit(xdata_reshape, ydata)
        pred  = reg.predict(np.array([[x]], dtype=object))
        return pred[0]

    def est_ref_time_reg(self):
        """
        This function estimates the reference time based on the local time and the reference time provided.
        
        :return: The function `est_ref_time_reg` returns the estimated reference time based on the current
        local time, reference time, and continuous local time. If the length of the reference time is
        greater than 2, the function calls `get_ref_time_estimate` to calculate the estimated time.
        Otherwise, the estimated time is set to the continuous local time. The function returns the
        estimated time.
        """
        if len(self.ref_time) > 2:
            est_time = self.get_ref_time_estimate(self.loc_time, self.ref_time, self.cont_local_time)
        else: 
            est_time = self.cont_local_time
        return est_time

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        self._stats = stats
        self.active_clock.stats = stats
        self.persistent_clock.stats = stats

        self.stats.register_time_series(StatType.SUCC_COMM)
