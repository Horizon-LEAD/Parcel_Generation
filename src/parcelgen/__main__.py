"""
parcelgen

Generates parcels
"""

from os import getcwd
from os.path import isfile, join, abspath
from sys import argv
from dotenv import dotenv_values
from argparse import (ArgumentParser, RawTextHelpFormatter,
                      ArgumentDefaultsHelpFormatter, ArgumentTypeError)

from .utils import parse_env_values, parse_params_file
from .proc import run_model


class RawDefaultsHelpFormatter(ArgumentDefaultsHelpFormatter, RawTextHelpFormatter):
    """Argparse formatter class"""


def strfile(path):
    """Argparse type checking method
    string path for file should exist"""
    if isfile(path):
        return path
    raise ArgumentTypeError("Input file does not exist")


def main():
    parser = ArgumentParser(description=__doc__,
                            formatter_class=RawDefaultsHelpFormatter)
    parser.add_argument('-v', '--verbosity', action='count',
                        default=0, help='Increase output verbosity')
    parser.add_argument('-e', '--env', type=strfile, default=join(getcwd(), ".env"),
                        help='Use .env file')
    parser.add_argument('--gui', action='store_true', default=False,
                        help='Use .env file')
    
    args = parser.parse_args(argv[1:])
    print(f"INFO: using env file: {abspath(args.env)}")
    
    config = parse_env_values(dotenv_values(abspath(args.env)))
    params = parse_params_file(config['PARAMS_FILE'])
    config.update(params)
    for key, value in config.items():
        print(f'{key:<30s}: {value}')
    # environ.update(config)
    
    if args.gui:
        from .ui import ParcelGenUI

        root = ParcelGenUI(config)
        print(root.returnInfo)

        return root.returnInfo
    
    run_model(config)


if __name__ == "__main__":
    main()
