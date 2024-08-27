# Generating shared sense of time error results using Lure

To run a multinode experiments with different lifecycle ratios of nodes in the network. The configuration given in `config-grid-r3xc3`, which generates a 3 by 3 grid BISN, can be used.

## Setting a LMP config

To change the LMP configuration of each node, we can change the `on_time_ms` to a value that corresponds to a correct LMP config for each node in the series given in `multinode_experiment.json` . For instance, to get a LMP config of 2, we can input `"on_time_ms": 10` because 2 multiplied by 5 ms which is default value of `slot_length` is equals to 10 ms. Similarly, to get a LMP config of 30, we must input `"on_time_ms": 150`.

```json
"lmp": {
    "class": "FixedLMP",
    "on_time_ms": 10
}
```

## Setting a series of lifecycle ratios (LCRs)

Since we are sweeping through a range of LCR values for each node, we must provide a list of LCR values. The LCR for each node can be provided using the following harvester config in the corresponding node specific `n{node_id}_node.json` json file. For example, in `n0_node.json`, we specify highest LCR among all the nodes assuming energy harvesting source is placed closest to `node 0` as shown below. The average lifecycle ratio can be calculated by taking mean of LCR value at the same index of each node in the `"lifecycle_ratio` list.

```json
"node_id": 0,
"power_supply": {
    "harvester": {
        "lifecycle_ratio": [
            0.05,
            0.1,
            0.25,
            0.42,
            0.63,
            0.83
        ]
    }
}
```

## Running Simulation

The simulation can be started using the following command:

```bash
python run.py
```

For each LMP config (selected using the above steps), run the simulation. This will generate `N` number of simulation directories that corresponds to each LMP config. Each directory name will be timestamped with start time of the simulation.

Note: it is recommended to use python virtual env and install all dependencies before running simulations in Lure.

## Plotting results

After running separate simulations for each LMP config, there will be multiple simulation directories. To generate plot with lifecycle ratios on x-axis and shared sense of time error on y-axis, following command can be used:
```
    python analyzer.py -d [simulation output dirs] -x [lcr values] -c [LMP config values]
```

For example, to plot the default results:
```
    python analyzer.py -d output_sim_3x3_2_<datetime> output_sim_3x3_10_<datetime> output_sim_3x3_30_<datetime> output_sim_3x3_50_<datetime> -x 0.01 0.02 0.05 0.10 0.15 0.20 -c 2 10 30 50
```

The analyzer script generates pickle files of the error and then plots it using plotting scripts.
