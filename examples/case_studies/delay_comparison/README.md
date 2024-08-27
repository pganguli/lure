# Delay Comparison of Lure Simulator to Analytic Model.

## Simulator Delay Results
This example configuration produces results for delay comparison of simulator vs analytical model. To run the experiments, invoke Lure as a module:

    python -m lure

To plot the results, run plot.py:

    python plot.py

The plots will be placed in 'output/figures/'

## Analytic Model Results
By setting lcr value, the charging powers of the nodes are obtained. For a given LMP-X config, the ontime of a node = bootime + X * slot length.


