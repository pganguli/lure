import os
import argparse
from multiprocessing import Pool
import pickle

from lure.results import LURE_RESULTS_FILENAME, ExperimentResult, LureResults, SeriesResult, SimulationResult
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import shutil
import subprocess
from datetime import datetime
from typing import List

from lure.config.configuration import LureConfig
from lure.experiment import Experiment
from alive_progress import alive_bar
from email.message import EmailMessage
import smtplib
 
class Lure:
    """Core simulation class

    :param config_dir: Path to directory containing the configuration files
    :type config_dir: str
    :param top_config_file: The filename of the top level configuration file (path is from the perspective of config_dir)
    :type top_config_file: str
    :param output_dir: Path to output directory, defaults to 'output'
    :type output_dir: str, optional
    :param resume: When true, Lure will attempt to pick up the simulation from the first uncompleted trial in the configuration files. \
        Else, Lure creates a new output directory and starts the simulation from the beginning, defaults to True
    :type resume: bool, optional
    :param exps: By default, all experiments are run. If a list indices are provided, Lure will index the experiments in the top level configuration file and only run experiment indices provided
    :type exps: List[int], optional
    :param progress_bar: When True, a progress bar is displayed that details the number of experiments, series, and x values left to simulate, defaults to True
    :type progress_bar: bool, optional
    :param email_notify: When True, Lure looks for email configurations in the top level configurations file to send an email notification upon completion of :py:meth:`lure.run`, defaults to False
    :type email_notify: bool, optional
    """

    @classmethod
    def convert_to_lazy(cls, output_dir: str):
        '''Convert prior versions of Lure results format stored on disk to the new format. Doesn't change result pickle files,
        just adds a new pickled LureResults object that defines the layout of the results. Automatically called when older
        results are loaded via `load_results()`.
        
        :param output_dir: The results directory to convert
        :type output_dir: str
        '''
        lure_results = LureResults()
        with os.scandir(f'{output_dir}/results') as lure_it:
            exp_entries = sorted(lure_it, key=lambda e: e.name)
            for exp_entry in exp_entries:
                if exp_entry.is_dir():
                    # Experiment dir
                    exp_result = ExperimentResult()
                    lure_results.add_experiment(exp_result)
                    with os.scandir(exp_entry.path) as exp_it:
                        for series_entry in exp_it:
                            if series_entry.is_dir():
                                # Series dir
                                with open(f'{series_entry.path}/metadata.p', 'rb') as f:
                                    metadata = pickle.load(f)
                                series_result = SeriesResult(key=metadata.key, output_dir=series_entry.path, plot_config=metadata.plot_config)
                                exp_result.add_series(series_result)
                                for x_value in metadata.x_values:
                                    x_path = f'{series_entry.path}/{str(x_value)}'
                                    try:
                                        with os.scandir(x_path) as x_it:
                                            sim_entries = sorted(x_it, key=lambda e: e.name)
                                            for sim_entry in sim_entries:
                                                if sim_entry.is_dir():
                                                    series_result.add_simulation(x_value, int(sim_entry.name))
                                    except FileNotFoundError:
                                        print(f'{x_path} not found.')
        lure_results.write(f'{output_dir}/results')

    @classmethod
    def load_results(cls, output_dir: str = 'output') -> LureResults:
        """(Lazily) load results from the given output directory

        :param output_dir: Output directory, defaults to 'output'
        :type output_dir: str, optional
        :return: Returns the results of Lure stored in the output directory
        :rtype: LureResults
        """
        def _load_results(output_dir: str) -> LureResults:
            with open(f'{output_dir}/results/{LURE_RESULTS_FILENAME}', 'rb') as f:
                return pickle.load(f)

        try:
            lure_results = _load_results(output_dir)
        except FileNotFoundError:
            print('Info: LureResults file not found, attempting conversion from older results format.')
            Lure.convert_to_lazy(output_dir)
            lure_results = _load_results(output_dir)

        return lure_results

    def __init__(self, config_dir: str, top_config_file: str, output_dir: str = 'output', resume: bool = True, exps: List[int] = None, progress_bar: bool = True, email_notify: bool = False):

        self.output_dir = output_dir
        self.progress_bar = progress_bar
        self.email_notify = email_notify

        self.exps = exps

        if not resume:
            try:
                shutil.move(self.output_dir, f'{self.output_dir}_{datetime.now().strftime("%Y%m%d%H%M%S")}')
            except FileNotFoundError:
                pass

        os.makedirs(self.output_dir, exist_ok=True)

        self.lure_config = LureConfig(config_dir, top_config_file)
        self.lure_config.to_file(f'{self.output_dir}/final_config.json')
        with open(f'{self.output_dir}/lure_version.txt', 'w') as f:
            subprocess.run(["git", "log", "-n", "1"], stdout=f)

        self.num_procs = None
        self.lure_config.extract('num_procs', self, 1)

        self.results: LureResults = LureResults()

        self.email_config = None
        self.lure_config.extract('email_config', self, None)



        if self.email_notify == True:
            try:
                test1 = self.email_config.get('sender')
                test2 = self.email_config.get('recipients')
                test3 = self.email_config.get('server')
                test4 = self.email_config.get('body')
                if not (test1 and test2 and test3 and test4):
                    raise KeyError
            except:
                print("EMAIL CONFIG ERROR: Email configuration item was not found or improperly formatted")
                raise

    def run(self):
        """Runs experiments specified in the Lure configuration
        """
        results_dir = f'{self.output_dir}/results'

        exp_total = len(self.lure_config.experiments)
        if self.num_procs > 1:
            with Pool(self.num_procs) as p:
                for i, exp in enumerate(self.lure_config.experiments):
                    if self.exps and i not in self.exps:
                        continue
                    experiment = Experiment(exp, output_dir = f'{results_dir}/{i}')
                    total_exp_steps = len(experiment.series) * len(experiment.series[0].x_values) # total = series * x_vals
                    if self.progress_bar:    
                        with alive_bar(total_exp_steps, title=f'Experiment {i + 1}/{exp_total}') as bar:
                            self.results.add_experiment(experiment.run(p, progress_bar=bar))
                    else:
                        self.results.add_experiment(experiment.run(p))
        else:
            for i, exp in enumerate(self.lure_config.experiments):
                if self.exps and i not in self.exps:
                    continue
                experiment = Experiment(exp, output_dir = f'{results_dir}/{i}')
                total_exp_steps = len(experiment.series) * len(experiment.series[0].x_values) # total = series * x_vals
                if self.progress_bar: 
                    with alive_bar(total_exp_steps, title=f'Experiment {i + 1}/{exp_total}') as bar:
                        self.results.add_experiment(experiment.run(progress_bar=bar))
                else:
                    self.results.add_experiment(experiment.run())

        self.results.write(results_dir)
        
        if self.email_notify == True:
            msg = EmailMessage()
            msg.set_content(self.email_config['body'])
            msg['Subject'] = f'Lure Notification!'
            msg['From'] = self.email_config['sender']
            msg['To'] = ', '.join(self.email_config['recipients'])

            s = smtplib.SMTP(self.email_config['server'])
            s.send_message(msg)
            s.quit()

        


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Lure, the LMP simulator.')
    parser.add_argument('-C', type=str, default='config', help='Configuration directory.')
    parser.add_argument('-c', type=str, default=None, help='Top-level configuration file (e.g. lifecycle_ratio.json).')
    parser.add_argument('-o', type=str, default='output', help='Output directory.')
    parser.add_argument('--resume', type=bool, default=False, help='Keep existing results and run any trials without existing results.')
    args = parser.parse_args()

    simulator = Lure(config_dir=args.C, top_config_file=args.c, output_dir=args.o, resume=args.resume)
    simulator.run()
