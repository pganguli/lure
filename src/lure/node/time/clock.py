from lure.config.configuration import Config
from lure.lure_logger import Loggable
from lure.node.stats import StatsProvider


class Clock(Loggable, StatsProvider):
    """An object that represents a clock for a node."""

    def __init__(self, config: Config):
        """Instantiates a Clock.

        :param config: a configuration object
        :type config: Config
        """
        self.t: float = 0

    def update(self, t: float) -> float:
        """Updates the clock for a given amount of ground truth time, and returns the amount the clock changed

        :param t: the amount of ground truth time (in ms) that has passed since the last time this method was called
        :type t: float
        :return: the amount of time the clock changed this update, which may be different than the ground truth time due to various sources of error
        :rtype: float
        """
        self.t += t
        return t

    def reset(self):
        """Resets the clock to zero"""
        self.t = 0

    def clock(self) -> float:
        """Returns the current value of the clock

        :return: the current clock reading
        :rtype: float
        """
        return self.t
