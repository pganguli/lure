from lure.lure import Lure
from lure.node.stats import StatType

old_results = Lure.load_results('example_output')
new_results = Lure.load_results('output')

print('Diffing new results vs. results in example_output/...')

same = True

for old_exp_result, new_exp_result in zip(old_results, new_results):
    for series_key, new_series_result in new_exp_result.items():
        old_series_result = old_exp_result.series_results[series_key]
        for x_value in new_series_result.x_values:
            try:
                old_sim_results = old_series_result.sim_results[x_value]
            except KeyError:
                if x_value is None:
                    # Backwards compatibility with older x value system
                    old_sim_results = old_series_result["Unknown"]
                else:
                    raise KeyError
            new_sim_results = new_series_result.sim_results[x_value]
            for old_sim_result, new_sim_result in zip(old_sim_results, new_sim_results):
                for old_stats, new_stats in zip(old_sim_result, new_sim_result):
                    diff_keys, diff_ts_keys = new_stats.intersection_diff(old_stats)
                    if diff_keys or diff_ts_keys:
                        same = False
                        for k in diff_keys:
                            print(f'Difference found for stat {k} for node {new_stats.get(StatType.NODE_ID)} series {series_key}, x-value {x_value}.')
                            print(f'\tOld value: {old_stats.get(k)}')
                            print(f'\tNew value: {new_stats.get(k)}')
                        for k in diff_ts_keys:
                            print(f'Difference found for time series {k} for series {series_key}, x-value {x_value}.')

if same:
    print('Results are the same.')
    exit(0)

print('One or more differences found.')
exit(1)
