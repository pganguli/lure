import argparse

from lure.lure import Lure


parser = argparse.ArgumentParser(description='Lure, a batteryless intermittent network simulator.')
parser.add_argument('-C', type=str, default='config', help='Configuration directory. Default is "config"')
parser.add_argument('-c', type=str, default='lure.json', help='Top-level configuration file. Must be in the config directory. Default is "lure.json"')
parser.add_argument('-o', type=str, default='output', help='Output directory. Default is "output"')
parser.add_argument('--resume', action='store_true', help='Keep existing results and run any trials without existing results.')
parser.add_argument('-e', type=int, nargs='+', help='Select experiments to run (by index).')

args = parser.parse_args()

simulator = Lure(config_dir=args.C, top_config_file=args.c, output_dir=args.o, resume=args.resume, exps=args.e)
simulator.run()