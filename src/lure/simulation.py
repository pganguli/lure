import copy
import pickle
import sys
import time

from lure.grapher import Grapher
from typing import List, Union
from lure.config.configuration import LoggerConfig
from lure.energy.energy_model import EnergyModel
from lure.energy.static_dist_energy_model import *

import simpy

from lure.lure_logger import Loggable, LureLogger
from lure.node.sensor_node import SensorNode
from lure.node.stats import StatName, StatType, Stats, StatsObserver

MIN_EXE_TIME = 1 # ms

class Simulation(Loggable, StatsObserver):
    """The simulate class. Assumption about this simulation: (1) assume the energy harvesting rate is fixed with distance from the RF tX power, 
    and (2) two nodes will communicate successfully with each other if the overlap period is greater than "MIN_COMM_TIME", which is defined in
    :py:mod:`lure.node.sensor_node`

    """    
    
    def __init__(self, energy_model: EnergyModel, nodes: List[SensorNode], logger_config: LoggerConfig, max_time: int = 0, max_packets: int = 0, output_dir: str='output', seed: int=1):
        import random
        random.seed(a=seed)

        self.seed = seed

        self.label = f'energy-{energy_model}_n-{len(nodes)}_{nodes[0]}_seed-{seed}'

        self.nodes = copy.deepcopy(nodes)
        self.max_time = max_time
        self.max_packets = max_packets
        self.packets_so_far = 0
        self.max_packet_event = None

        self.output_dir = output_dir

        self.t = 0
        self.min_exe_time = MIN_EXE_TIME

        self.simpy_env = simpy.Environment()

        node_ids = []
        for n in self.nodes:
            node_ids.append(n.node_id)
        self.logger = LureLogger(logger_config, self.simpy_env, output_dir=self.output_dir)
        self.start_time = None

        self.register_log(self.logger, logger_config.get_level("simulation"), 'Simulation')

        self.energy_model = energy_model
        self.energy_model.register_log(self.logger, logger_config.get_level("energy_model"), 'EnergyModel')
        self.energy_model.initialize(self)
        self.simpy_env.process(self.energy_model.execute(self.simpy_env))

        for n in self.nodes:
            n.init_with_simulation(self, self.logger)
            if self.max_packets and self.max_packets > 0:
                n.stats.add_observer(self)
            n.process = self.simpy_env.process(n.execute(self.simpy_env, self.energy_model))           
            
    def get_node_by_id(self, node_id):
        """Retrieves the :py:class:`lure.node.sensor_node.SensorNode` object with the node_id corresponding to the node belonging to this simulation

        :param node_id: Address for the SensorNode object to be returned
        :type node_id: int
        :return: Desired node
        :rtype: SensorNode
        """
        try:
            return [n for n in self.nodes if n.node_id == node_id][0]
        except IndexError as e:
            return None
        
    def run(self):
        """Start the simulation and graphs the topologies using :py:mod:`lure.grapher`
        """
        self.start_time = time.time()
        self.info('--------simulation starts--------')
        self.info(f'Sim label: {self.label}')
        if self.max_packets and self.max_packets > 0:
            self.info(f'Running for {self.max_packets} packets')
            self.max_packet_event = self.simpy_env.event()
            self.simpy_env.run(until=self.max_packet_event)
            # Can't pickle generator objects, yo
            self.max_packet_event = None
        else:
            self.info(f'Running for {self.max_time} simulated ms')
            self.simpy_env.run(until=self.max_time)
        self.info('--------simulation ends--------')
        self.logger.close()
        
        grapher = Grapher(self.nodes, self.output_dir)
        grapher.graph_network()
        grapher.graph_physical()

        for n in self.nodes:
            n.close(self.output_dir)
        with open(f'{self.output_dir}/results.p', 'wb') as f:
            pickle.dump([n.stats for n in self.nodes], f)

    def on_update(self, name: StatName, val_change: Union[int, float], stats: Stats):
        """Implements the abstract method :py:meth:`lure.node.stats.StatsObserver.on_update` to check if end-of-simulation conditions are met

        :param name: Name of the stat to track
        :type name: StatName
        :param val_change: Value to change to
        :type val_change: Union[int, float]
        :param stats: Stats object to record this change
        :type stats: Stats
        """
        if name == StatType.PACKETS_RECEIVED_APP and self.max_packets and self.max_packets > 0:
            self.packets_so_far += val_change
            cur_time = time.time()-self.start_time
            elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - self.start_time))
            self.debug(f'{self.packets_so_far} packets sent app, real_time={elapsed}, seconds={cur_time}')
            if self.packets_so_far >= self.max_packets:
                self.max_packet_event.succeed()

