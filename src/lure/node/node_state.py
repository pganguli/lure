from enum import Enum


class NodeState(Enum):
    """Power states a node can be in"""

    OFF = "off"
    BOOTING = "booting"
    OPERATING = "operating"
    SLEEPING = "sleeping"
