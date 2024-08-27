# Network Case Study
This example configuration evaluates network-level performance using baseline communication protocols in a ring topology.

To run the experiment, use:

    python run.py
    
*NOTE: The experiment will utilize 20 processes via the multiprocessing feature. This can be adjusted by changing the num_procs value within `config/top.json`.*

To plot the results, run:

    python plot.py
    
and open the `output/figures` directory it creates. Two figures will be created.
The figure named `packet_delivery_ratio_0.2.pdf` shows end-to-end delivery ratio in the network when all nodes have 0.2 as their LCR.
The figure named `packet_delivery_ratio_0.02.pdf` shows the same scenario, except that node 0 has a lower LCR of 0.02.