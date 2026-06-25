from lure.node.time.time import TimeModule


class PerfectTimeModule(TimeModule):
    # Returns a perfect continuous sense of time
    def time(self) -> int:
        """
        The function returns the current time in the simulation.
        :return: an integer value, which is the current time in the simulation.
        """
        return self.timestepper.simpy_env.now
