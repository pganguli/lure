from typing import Dict, Tuple
from simpy import Interrupt
from simpy.core import SimTime, Environment, Process

from lure.lure_logger import Loggable


class Timestepper(Loggable):
    """Controls the progression of simulation time using the SimPy framework"""

    def __init__(self):
        self._timers: Dict[str, SimTime] = dict()
        self.process: Process = None

    def initialize(self, simpy_env: Environment):
        """Initialize Timestepper with the start of the simulation

        :param simpy_env: The environment SimPy will operate in
        :type simpy_env: Environment
        """
        self.simpy_env = simpy_env

    def timer_expired(self, key: str) -> bool:
        """Checks to see whether a Timestepper timer has expired. One use case is to check for timeout conditions

        :param key: A key used to select which timer to check
        :type key: str
        :return: True if the timer has expired. False if the timer hasn't expired or does not exist
        :rtype: bool
        """
        try:
            return self.simpy_env.now >= self._timers[key]
        except KeyError:
            self.warning(f"Timer {key} not found.")
            return False

    def cancel_timer(self, key: str):
        """Cancels a set timer

        :param key: A key used to select a timer
        :type key: str
        """
        self._timers[key] = -1

    def set_relative_timer(self, key: str, t: SimTime):
        """Sets a timer for some point in the simulated future

        :param key: A key used to select a timer
        :type key: str
        :param t: The duration to wait before the timer expires at time (now + t)
        :type t: SimTime
        """

        # If the new time is now the earliest time, we should add a new timeout event.
        self.debug(f"Setting {key} with {t}")
        self._timers[key] = self.simpy_env.now + t

        if self.process is not None:
            _, min_t = self._find_next_timestep()
            if min_t == self._timers[key]:
                try:
                    self.process.interrupt()
                    self.debug("Interrupting process.")
                except RuntimeError as e:
                    self.debug(f"Tried to interrupt self {e}")

    def _find_next_timestep(self) -> Tuple[str, SimTime]:
        """Finds the next timer to expire

        :return: The key and value of the timer that expires next
        :rtype: Tuple[str, SimTime]
        """
        min_key = None
        min_t = None
        for k, t in self._timers.items():
            if t > self.simpy_env.now and (min_key is None or t < min_t):
                min_t = t
                min_key = k
        if min_key is None:
            return None, 1
        return min_key, min_t

    def next_timestep(self, process: Process):
        """Yield until the next timestep is reached

        :param process: The process being managed by Timestepper
        :type process: Process
        """
        self.process = process
        while True:
            key, time = self._find_next_timestep()
            self.debug(f"Yielding for {time - self.simpy_env.now}")
            try:
                yield self.simpy_env.timeout(time - self.simpy_env.now)
                self.debug("Timed out normally.")
                key, time = self._find_next_timestep()
                if key is None or self._timers[key] == time:
                    break
                else:
                    self.debug("False alarm, continuing to yield.")
            except Interrupt:
                self.debug("Interrupted timeout.")
                break
