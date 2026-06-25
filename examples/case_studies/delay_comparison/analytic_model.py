import numpy as np


lcr = 0.030
Pon = 50  # ontime power consumption(mW)
P0 = lcr * Pon  # charging power(mW) for node 0
P1 = lcr * Pon  # charging power(mW) for node 1
s = 5  # communication slot length(ms)
boottime = 15
Tmin = boottime + s  # minimum ontime(ms)
Tmax = 160  # maximum ontime(ms)


"""
ontimes
:T0_ontimes: Node 0 ontimes
:T1_ontimes: Node 1 ontimes
"""
T0_ontimes = [25, 115]
T1_ontimes = [25, 115]


def expectedTTO(T0, T1):
    Z = (Pon * Pon * T0 * T1) / (P0 * P1 * (T0 + T1 + -2 * boottime - s))
    return Z


def expectedThroughput(T0, T1):
    m = T0 // s
    n = T1 // s
    K = Tmax // s
    b = boottime // s
    X = np.sum([K - i for i in range(b, m)]) + np.sum([K - i for i in range(b + 1, n)])
    return (P0 * P1 * s * X) / (T0 * T1 * Pon * Pon)


TTOs = {
    (np.divide(T0 - boottime, s), np.divide(T1 - boottime, s)): expectedTTO(T0, T1)
    / 1000
    for T0 in T0_ontimes
    for T1 in T1_ontimes
}

throughputs = {
    (np.divide(T0 - boottime, s), np.divide(T1 - boottime, s)): expectedThroughput(
        T0, T1
    )
    * 1000
    for T1 in T1_ontimes
    for T0 in T0_ontimes
}
