# Trace example
This example is a short experiment with one trial for one configuration. It produces trace plots for this experiment, i.e. time series plots that show various data values over the course of the simulation.

To run the experiment, invoke Lure as a module:

    python -m lure

To plot the results, use:

    python plot.py

## Regression tests
The output of this experiment is also used in regression tests. The test script `tests/diff_example.py` runs the experiment and compares the `Stats` output to the `example_output/` directory found here. If changes are made to Lure core that affect the output of this experiment, the `example_output/` directory should be replaced with a fresh copy of the output (after verifying that the new results are correct). To do this:

    python -m lure
    python plot.py
    rm -r example_output
    mv output example_output