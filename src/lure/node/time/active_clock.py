from lure.config.configuration import Config
from lure.node.time.clock import Clock


class ActiveClock(Clock):
    """An object representing the active clock for a node, i.e., the clock that runs when the node is on."""

    def __init__(self, config: Config):
        super().__init__(config)
        self.skew = 0
        self.drift = 0
        config.extract("skew", self, 0)
        config.extract("drift", self, 0)

    def update(self, t: float) -> float:
        self.t += t
        return t
