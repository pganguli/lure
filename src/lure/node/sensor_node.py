import random
import simpy
from typing import TYPE_CHECKING
from lure.energy.energy_model import EnergyModel

from lure.node.node_state import NodeState
from lure.node.timestepper import Timestepper
if TYPE_CHECKING:
    from lure.simulation import Simulation
from lure.config.configuration import Config, LoggerConfig, SensorNodeConfig
from lure.lure_logger import Loggable, LureLogger
from lure.node.lmp.lmp import LMP
from lure.node.net.netstack import Netstack
from lure.node.net.packet import Packet
from lure.node.power.power_supply import PowerSupply
from lure.node.time.time import TimeModule
from lure.node.traffic.traffic_generator import TrafficGenerator
from lure.node.stats import StatType, Stats, StatsProvider

class SensorNode(Loggable, StatsProvider):
    """A sensor node object to be simulated
    """
    def __init__(self, config: SensorNodeConfig):
        self.radio_discharge_rate_w = None
        self.boot_discharge_rate_w = None
        self.sleep_discharge_rate_w = None
        self.os_boot_time_ms = None
        self.clock_read_time_ms = None
        self.node_id = None

        config.extract("radio_discharge_rate_w", self, 0.06)
        config.extract("boot_discharge_rate_w", self, 0.042)
        config.extract("sleep_discharge_rate_w", self, 0.00255)
        config.extract("os_boot_time_ms", self, 15)
        config.extract("clock_read_time_ms", self, 0)
        config.extract("node_id", self, 0)

        self._perfect_clock = 0
        self.prev_t = 0
        self._state: NodeState = None

        self.discharge_rates = {
            NodeState.OFF: 0,
            NodeState.BOOTING: self.boot_discharge_rate_w,
            NodeState.OPERATING: self.radio_discharge_rate_w,
            NodeState.SLEEPING: self.sleep_discharge_rate_w
        }

        self.time_module: TimeModule = Config.instantiate_from_dict(config.config["time_module"], 'lure.node.time')
        self.power_supply: PowerSupply = Config.instantiate_from_dict(config.config["power_supply"], 'lure.node.power')
        self.lmp: LMP = Config.instantiate_from_dict(config.config["lmp"], 'lure.node.lmp')
        self.netstack: Netstack = Config.instantiate_from_dict(config.config["netstack"], 'lure.node.net')
        self.netstack.set_addr(self.node_id)
        self.traffic_generator: TrafficGenerator = Config.instantiate_from_dict(config.config["traffic_generator"], 'lure.node.traffic')

        self.stats: Stats = Stats(config.stats, label=f'node{self.node_id}')

        self.logger_config = LoggerConfig(config.config["logger"])

        self.on_neighbors = {}
        self.comm_setup = {}

        self.last_off_time = -1
        self.last_on_time = -1

        self.process = None
        self.timestepper: Timestepper = Timestepper()

    @property
    def state(self) -> NodeState:
        """This node object's current power state

        :return: Current power state
        :rtype: NodeState
        """
        return self._state

    @state.setter
    def state(self, new_state: NodeState):
        if new_state != self._state:
            self.debug(f'Node state changed from {self._state} to {new_state}')
            self.stats.time_series_append(StatType.NODE_STATE, new_state)
            self._state = new_state

    @StatsProvider.stats.setter
    def stats(self, stats: Stats):
        """Declares stats for submodules

        :type stats: Stats
        """
        self._stats = stats
        self.time_module.stats = stats
        self.power_supply.stats = stats
        self.lmp.stats = stats
        self.netstack.stats = stats
        self.traffic_generator.stats = stats

        self.stats.register(StatType.NODE_ID, self.node_id)
        self.stats.register_time_series(StatType.NODE_OFFTIME)

    def init_with_simulation(self, sim: 'Simulation', logger: LureLogger):
        """An secondary initialization after the simulation has been instantiated. Calls initialize() on all submodules

        :param sim: The sim that this node belongs to
        :type sim: Simulation
        :param logger: Logger for this node
        :type logger: LureLogger
        """
        # TODO: remove this after adding network layer
        self.simulation = sim

        self.stats.initialize(sim)

        node_tag = f'{self.node_id}'
        # self.register_log(logger, self.logger_config.get_level("node"), node_tag)
        self.register_log(logger, self.logger_config.get_level("node"), f'{node_tag}')
        self.timestepper.register_log(logger, self.logger_config.get_level("node"), f'{node_tag}{logger.sep}Timestepper')
        self.lmp.register_log(logger, self.logger_config.get_level("lmp"), f'{node_tag}{logger.sep}LMP')
        self.netstack.mac.register_log(logger, self.logger_config.get_level("mac"), f'{node_tag}{logger.sep}MAC')
        self.netstack.ill.register_log(logger, self.logger_config.get_level("ill"), f'{node_tag}{logger.sep}ILL')   
        self.netstack.network.register_log(logger, self.logger_config.get_level("network"), f'{node_tag}{logger.sep}NETWK')
        self.netstack.physical.register_log(logger, self.logger_config.get_level("physical"), f'{node_tag}{logger.sep}PHYS')
        self.netstack.ill.send_queue.register_log(logger, self.logger_config.get_level("queue"), f'{node_tag}{logger.sep}PacketQueue')   
        self.power_supply.register_log(logger, self.logger_config.get_level("power_supply"), f'{node_tag}{logger.sep}PowerSupply')
        self.power_supply.storage.register_log(logger, self.logger_config.get_level("power_supply"), f'{node_tag}{logger.sep}Storage')
        self.power_supply.harvester.register_log(logger, self.logger_config.get_level("power_supply"), f'{node_tag}{logger.sep}Harvester')
        self.traffic_generator.register_log(logger, self.logger_config.get_level("traffic"), f'{node_tag}{logger.sep}TrafficGenerator')
        self.time_module.register_log(logger, self.logger_config.get_level("time"), f'{node_tag}{logger.sep}TimeModule')        

        self.timestepper.initialize(sim.simpy_env)
        self.traffic_generator.initialize(self)
        self.time_module.initialize(self)
        self.power_supply.initialize(self, self.simulation.energy_model)
        if self.power_supply.get_time_to_restart() is not None and self.power_supply.get_time_to_restart() <= 0:
            self.restart()
        else:
            self.state = NodeState.OFF
        self.lmp.initialize(self)
        self.netstack.initialize(self, [n.netstack for n in sim.nodes if n is not self], sim.simpy_env)

    def close(self, output_dir: str):
        """Closes this nodes files

        :param output_dir: The output directory
        :type output_dir: str
        """
        self.simulation = None

        self.stats.set(StatType.SIMULATION_TIME, self.prev_t)

        if self.state is NodeState.OFF:
            try:
                die_time = self.stats.get_time_series(StatType.NODE_DIE)[-1][0]
                self.stats.update(StatType.NODE_TOTAL_OFFTIME, self.prev_t - die_time)
            except TypeError:
                pass

        ontime = self.stats.get(StatType.NODE_TOTAL_ONTIME)
        if ontime:
            self.stats.set(StatType.NODE_LIFECYCLE_RATIO, ontime / self.prev_t)

        self.stats.close(output_dir)

    def get_avg_discharge_power_w(self):
        """Retrieves the average power discharge on this node

        :return: Average discharge rage
        """
        Eon = self.power_supply.get_max_ontime_energy()
        max_ontime = (Eon - self.os_boot_time_ms * (self.discharge_rates[NodeState.BOOTING] - self.discharge_rates[NodeState.OPERATING])) / self.discharge_rates[NodeState.OPERATING]
        boot_fraction = self.os_boot_time_ms / max_ontime #(self.os_boot_time_ms + self.lmp.get_avg_ontime_ms(max_ontime - self.os_boot_time_ms))

        return self.discharge_rates[NodeState.BOOTING] * boot_fraction + self.discharge_rates[NodeState.OPERATING] * (1 - boot_fraction)

    def __str__(self):
        return f'nid-{self.node_id}_power-{self.power_supply}_lmp-{self.lmp}_net-{self.netstack}_traffic-{self.traffic_generator}'

    def execute(self, simpy_env: simpy.core.Environment, energy_model: EnergyModel):
        """SimPy process for a node. Execution for this node on every time interval of the simulation

        :param simpy_env: The simpy environment that all nodes in the simulation operate in
        :type simpy_env: simpy.core.Environment
        :param energy_model: Energy model assigned to this node
        :type energy_model: EnergyModel
        """
        # One iteration of this loop == one timestep of a node's execution. At the end of the loop, we yield
        # for an amount of time depending on whether the node is on or not. If the node is on, we currently
        # step through every ms. If the node is off, we yield until it is time to turn on again, according to
        # the charging model.
        while True:
            elapsed_t = simpy_env.now - self.prev_t
            self.prev_t = simpy_env.now

            if self.state is NodeState.OFF:
                self.stats.update(StatType.NODE_TOTAL_OFFTIME, elapsed_t)
            else:
                self.stats.update(StatType.NODE_TOTAL_ONTIME, elapsed_t)

            self.info(f'Node {self.node_id} executing at time {self.prev_t}')

            # Things we do regardless of whether the node is on or off
            above_minimum_voltage = self.power_supply.execute(self.discharge_rates[self.state])
            #self.traffic_generator.generate()

            # Things we do if the node is off
            if self.state is NodeState.OFF:
                time_to_restart = self.power_supply.get_time_to_restart()
                if time_to_restart is not None:
                    if time_to_restart <= 0:
                        self.restart()
                    else:
                        self.debug(f'Not time to restart yet.')

            # Consume!
            else:
                if not above_minimum_voltage:
                    self.die()
                    self.info(f'Dies due to no energy')

                # Things we do if the node is on
                else:
                    # Things we do regardless of whether or not we have booted
                    self._perfect_clock += elapsed_t

                    # Things we do only after booting
                    if self._perfect_clock >= self.os_boot_time_ms:
                        self.debug('Booted')
                        # Boot if needed
                        if self.state is NodeState.BOOTING:# + RADIO_BOOTUP_TIME:
                            # Append off-time
                            if self.last_off_time > 0:
                                last_off_duration = self.last_on_time-self.last_off_time
                                self.stats.time_series_append(StatType.NODE_OFFTIME, last_off_duration)
                                self.debug(f" Node {self.node_id} was off for {last_off_duration} ms")
                            else:
                                last_off_duration = 0
                            
                            self.time_module.boot(last_off_duration+self.os_boot_time_ms)
                            self.lmp.boot()
                            self.netstack.boot()
                            self.netstack.network.register_receive_cb(self.app_receive_callback) 
                            self.netstack.network.register_sent_cb(self.app_sent_callback) 
                            
                            self.state = NodeState.OPERATING
                        

                            #TODO: does application trigger sending every time? Does application trigger receiving every time? Shen: Currently, yes
                            #TODO: somewhere we need to call self.netstack.ill.receive_async(), and the callback passed in needs to record comm stats. 
                            # Shen: as below.

                            # TODO: Temporary for overlap logging - DO NOT KEEP
                            for node in [n for n in self.simulation.nodes if n.node_id != self.node_id]:
                                if node.state is NodeState.OPERATING:
                                    self.debug('neighbor added')
                                    # adding to self and to the other node since one node turns on and checks neighbors before other is on
                                    node.on_neighbors[self.node_id] = simpy_env.now
                                    self.on_neighbors[node.node_id] = simpy_env.now
                                    self.debug(f'Overlap -- self: {self.on_neighbors}, node: {node.on_neighbors}')
                        #else:
                            # We don't want to both boot and execute the time module in the same timestep
                            

                        if self.state is NodeState.OPERATING:
                            # Things we do if we are booted
                            self.time_module.execute()
                            
                            num_generated_pkts = self.traffic_generator.generate()
                            if (num_generated_pkts > 0):
                                self.info(f'{num_generated_pkts} packets generated')

                                other_nodes = [n for n in self.simulation.nodes if n.node_id != self.node_id]

                                # send all nodes generated by application
                                for pkt in range(num_generated_pkts):
                                    rand_index = random.randint(0, (len(other_nodes)-1))
                                    destination_id = other_nodes[rand_index].node_id
                                    self.netstack.network.send_packet(destination_id, 'Hello world!')

                            elif self.netstack.ill.send_queue.queues_empty():
                                self.debug(f'queue is empty')

                            self.netstack.execute()

                        if self.state is NodeState.OPERATING or self.state is NodeState.SLEEPING:
                            next_state = self.lmp.execute()
                            if next_state is NodeState.OFF:
                                self.die()
                                self.info(f'Dies due to LMP enable')
                            elif self.state is NodeState.OPERATING and next_state is NodeState.SLEEPING:
                                self.sleep()
                            elif self.state is NodeState.SLEEPING and next_state is NodeState.OPERATING:
                                self.wake()

            # Decide how long to yield.
            self.set_state_timer()
            yield from self.timestepper.next_timestep(self.process)
            self.debug('Process waking...')

    def app_receive_callback(self, packet: Packet, sender_id: int):
        """Application layer callback for a successfully received packet

        :param packet: Packet received at the application layer
        :type packet: Packet
        :param sender_id: The node_id that sent the packet
        :type sender_id: int
        """
        self.debug(f'APP|Packet received from network, source node: {sender_id}, destination: {packet.destination_id}, payload: {packet.payload}')
        self.info(f'Packet received') 
        self.stats.increment(StatType.PACKETS_RECEIVED_APP)
        # do some application tasks here if needed...
        return

    def app_sent_callback(self, packet: Packet, status: bool):
        """The application layer callback for a sent packet

        :param packet: Packet sent to another node
        :type packet: Packet
        :param status: Boolean value for whether or not the packet was sent successfully
        :type status: bool
        """
        self.debug(f'APP|Sent packet: receiving node: {packet.next_hop}, status: {status}')
        if status:
            self.debug('Increment communication count')
            self.stats.increment(StatType.PACKETS_SENT_APP)

        # do some application tasks here if needed...

        return

    def restart(self):
        """Called when the node powers on from the OFF state
        """
        if self.state is not NodeState.OFF and self.state is not None:
            return

        self.stats.time_series_append(StatType.NODE_RESTART, self.time_module.time())
        self.state = NodeState.BOOTING
        self.power_supply.restart()
        self._perfect_clock = 0
        self.last_on_time = self.prev_t

        self.info(f'Node restarted')

    def die(self):
        """Called when the node is supposed to die
        """
        if self.state is NodeState.OFF:
            return

        self.stats.time_series_append(StatType.NODE_DIE, self.time_module.clock())

        self.debug(f'node {self.node_id} dies')
        # Temporary for overlap logging

        self.last_off_time = self.prev_t
        
        # TODO: Temporary
        self.on_neighbors = {}
        for node in [n for n in self.simulation.nodes if n.node_id != self.node_id]:
            if self.node_id in node.on_neighbors:
                self.debug('remove neighbor')
                del node.on_neighbors[self.node_id]

        self.state = NodeState.OFF
        
        self.netstack.mac.reset()
        self.time_module.off()

    def set_restart_timer(self):
        """Starts a restart timer for node to turn back on
        """
        time_to_restart = self.power_supply.get_time_to_restart()
        if time_to_restart is not None and time_to_restart > 0:
            self.timestepper.set_relative_timer('node_restart', time_to_restart)

    def sleep(self):
        """Sets the node to the sleep state
        """
        self.netstack.mac.reset()
        self.state = NodeState.SLEEPING

    def wake(self):
        """Tells the node to exit the sleep state and boot
        """
        self.state = NodeState.OPERATING
        self.netstack.boot()

    def set_state_timer(self):
        """Sets a state timer dependent on the current state
        """
        time_to_next = 0
        if self.state is NodeState.BOOTING:
            time_to_next = self.os_boot_time_ms - self._perfect_clock
        elif self.state is NodeState.OFF:
            time_to_next = self.power_supply.get_time_to_restart()
        elif self.state is NodeState.SLEEPING:
            time_to_next = self.lmp.get_time_til_wake()
            if time_to_next is None or time_to_next <= 0:
                time_to_next = self.power_supply.get_time_to_death(self.discharge_rates[NodeState.SLEEPING])
        elif self.state is NodeState.OPERATING:
            time_to_next = self.lmp.get_time_til_sleep()
            if time_to_next is None or time_to_next <= 0:
                time_to_next = self.power_supply.get_time_to_death(self.discharge_rates[NodeState.OPERATING])
        if time_to_next is not None:
            self.timestepper.set_relative_timer('node_state', max(time_to_next, 0.001))
