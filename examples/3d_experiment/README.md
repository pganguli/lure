# 3D Experiment example
This example runs a set of experiments that mimic the analysis and experiments presented in the below reference. These experiments evaluate communication between two nodes, where one node is the sender and the other is the receiver. The experiments sweep across a range of `FixedLMP` configurations for both nodes, and the full set of results is plotted as a 3D surface.

To run the experiments, invoke Lure as a module:

    python -m lure

To plot the results, use:

    python plot.py

The figures will be placed in `output/figures/`.

Reference: Deep, Vishal, et al. "Experimental Study of Lifecycle Management Protocols for Batteryless Intermittent Communication." 2021 IEEE 18th International Conference on Mobile Ad Hoc and Smart Systems (MASS). IEEE, 2021.