"""
parcelgen

Generates parcels
"""

import logging
from logging.handlers import RotatingFileHandler
from os import environ
from os.path import isfile, join, abspath, exists
from sys import argv
from argparse import (ArgumentParser, RawTextHelpFormatter,
                      ArgumentDefaultsHelpFormatter, ArgumentTypeError)

from dotenv import dotenv_values

from .utils import parse_env_values
from .ui import ParcelGenUI
from .proc import run_model


LOG_FILE_MAX_BYTES = 50e6
LOG_MSG_FMT = "%(asctime)s %(levelname)-8s %(name)s \
%(filename)s#L%(lineno)d %(message)s"
LOG_DT_FMT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("parcelgen")


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
    """Main method of Parcel Generation Model.
    """

    # command line argument parsing
    parser = ArgumentParser(description=__doc__,
                            formatter_class=RawDefaultsHelpFormatter)

    # parser.add_argument('LABEL', type=str, help='A label for the execution')
    parser.add_argument('PARAMS_FILE', type=strfile, help='The path of the params file (txt)')
    parser.add_argument('SKIMTIME', type=strfile, help='The path of the time skim matrix (mtx)')
    parser.add_argument('SKIMDISTANCE', type=strfile,
                        help='The path of the distance skim matrix (mtx)')
    parser.add_argument('ZONES', type=strfile, help='The path of the area shape file (shp)')
    parser.add_argument('SEGS', type=strfile, help='The path of the socioeconomics data file (csv)')
    parser.add_argument('PARCELNODES', type=strfile,
                        help='The path of the parcel nodes file (shp)')
    parser.add_argument('CEP_SHARES', type=strfile,
                        help='The path of the courier market shares file (csv)')
    parser.add_argument('EXTERNAL_ZONES', type=strfile,
                        help='The path of the external nodes file (csv)')
    parser.add_argument('OUTDIR', type=strdir, help='The output directory')

    parser.add_argument('-v', '--verbosity', action='count', default=0,
                        help='Increase output verbosity')
    parser.add_argument('--flog', action='store_true', default=False,
                        help='Stores logs to file')
    parser.add_argument('-e', '--env', type=str, default=None,
                        help='Defines the path of the environment file')
    parser.add_argument('--gui', action='store_true', default=False,
                        help='Displays the graphical user interface')

    args = parser.parse_args(argv[1:])

    # setting of the logger
    loglevel = 0
    if args.verbosity <= 0:
        loglevel = logging.ERROR
    elif args.verbosity == 1:
        loglevel = logging.WARNING
    elif args.verbosity == 2:
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG

    formatter = logging.Formatter(fmt=LOG_MSG_FMT, datefmt=LOG_DT_FMT)
    shandler = logging.StreamHandler()
    shandler.setFormatter(formatter)
    logger.addHandler(shandler)
    if args.flog:
        fhandler = RotatingFileHandler(
            join(args.OUTDIR, "logs.txt"),
            mode='w',
            backupCount=1,
            maxBytes=LOG_FILE_MAX_BYTES
        )
        fhandler.setFormatter(formatter)
        logger.addHandler(fhandler)

    logger.setLevel(loglevel)

    logger.debug('CMD : %s', ' '.join(argv))
    logger.debug('ARGS: %s', args)

    # setting of the configuration
    config = vars(args).copy()
    _ = [config.pop(key) for key in ("verbosity", "flog", "env", "gui")]
    config_env = {}
    if isfile(abspath(args.env)):
        logger.info("using env file: %s", abspath(args.env))
        config_env = parse_env_values(dotenv_values(abspath(args.env)))
    else:
        logger.info("using environment")
        config_env = parse_env_values(environ)
    config.update(config_env)
    logger.debug('CONFIG: %s', config)

    for key, value in config.items():
        print(f'{key:<30s}: {value}')

    if args.gui:
        root = ParcelGenUI(config)
        print(root.return_info)

        return

    run_model(config)


if __name__ == "__main__":
    main()
