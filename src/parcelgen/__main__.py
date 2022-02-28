"""
parcelgen

Generates parcels
"""

from os import getcwd, environ
from os.path import isfile, join, abspath, exists
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

def strdir(path):
    """Argparse type checking method
    string path for file should exist"""
    if exists(path):
        return path
    raise ArgumentTypeError("Input directory does not exist")


def main():
    parser = ArgumentParser(description=__doc__,
                            formatter_class=RawDefaultsHelpFormatter)
    
    # parser.add_argument('label', type=strdir, help='The directory of the input files')
    # parser.add_argument('params', type=strfile, help='The path of the params file (txt)')
    # parser.add_argument('time_skim', type=strfile, help='The path of the time skim matrix (mtx)')
    # parser.add_argument('distance_skim', type=strfile, help='The path of the distance skim matrix (mtx)')
    # parser.add_argument('area_shape', type=strfile, help='The path of the area shape file (shp)')
    # parser.add_argument('socioeconomics', type=strfile, help='The path of the socioeconomics data file (csv)')
    # parser.add_argument('parcel_nodes', type=strfile, help='The path of the parcel nodes file (shp)')
    # parser.add_argument('courier_shares', type=strfile, help='The path of the courier market shares file (csv)')
    # parser.add_argument('external_nodes', type=strfile, help='The path of the external nodes file (csv)')
    # parser.add_argument('output_dir', type=strdir, help='The output path')

    parser.add_argument('-v', '--verbosity', action='count', default=0, 
                        help='Increase output verbosity')
    parser.add_argument('-e', '--env', type=str, default=join(getcwd(), ".env"),
                        help='Defines the path of the environment file')
    parser.add_argument('--gui', action='store_true', default=False,
                        help='Displays the graphical user interface')
    
    args = parser.parse_args(argv[1:])

    config = {}
    if isfile(abspath(args.env)):
        print(f"INFO: using env file: {abspath(args.env)}")
        config = parse_env_values(dotenv_values(abspath(args.env)))
    else:
        print(f"INFO: using environment")
        config = parse_env_values(environ)

    print(config)

    params = parse_params_file(config['PARAMS_FILE'])
    config.update(params)
    for key, value in config.items():
        print(f'{key:<30s}: {value}')
    
    if args.gui:
        from .ui import ParcelGenUI

        root = ParcelGenUI(config)
        print(root.returnInfo)

        return root.returnInfo
    
    run_model(config)


if __name__ == "__main__":
    main()
