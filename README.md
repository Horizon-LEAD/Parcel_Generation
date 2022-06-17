# Parcel_Gen

_Parcel Generation model for the Living Lab of The Hague for the LEAD platform._

## Installation

The `requirements.txt` and `Pipenv` files are provided for the setup of an environment where the module can be installed. The package includes a `setup.py` file and it can be therefore installed with a `pip install .` when we are at the same working directory as the `setup.py` file. For testing purposes, one can also install the package in editable mode `pip install -e .`.

After the install is completed, an executable `parcelgen` will be available to the user.

## Usage

The executable's help message provides information on the parameters that are needed.

```
$ parcelgen -h
usage: parcelgen [-h] [-v] [--flog] [-e ENV] [--gui] PARAMS_FILE SKIMTIME SKIMDISTANCE ZONES SEGS PARCELNODES CEP_SHARES EXTERNAL_ZONES OUTDIR

parcelgen

Generates parcels

positional arguments:
  SKIMTIME           The path of the time skim matrix (mtx)
  SKIMDISTANCE       The path of the distance skim matrix (mtx)
  ZONES              The path of the area shape file (shp)
  SEGS               The path of the socioeconomics data file (csv)
  PARCELNODES        The path of the parcel nodes file (shp)
  CEP_SHARES         The path of the courier market shares file (csv)
  EXTERNAL_ZONES     The path of the external nodes file (csv)
  OUTDIR             The output directory

optional arguments:
  -h, --help         show this help message and exit
  -v, --verbosity    Increase output verbosity (default: 0)
  --flog             Stores logs to file (default: False)
  -e ENV, --env ENV  Defines the path of the environment file (default: None)
  --gui              Displays the graphical user interface (default: False)
```

Furthermore, the following parameters must be provided as environment variables either from the environment itself or through a dotenv file that is specified with the `--env <path-to-dotenv>` optional command line argument. An example of the `.env` file and some values is presented below.

```
LABEL='default'                         # * || 'UCC'

RUN_DEMAND_MODULE=true                  # boolean
CROWDSHIPPING_NETWORK=TRUE              # boolean
COMBINE_DELIVERY_PICKUP_TOUR=True       # boolean
HYPERCONNECTED_NETWORK=False            # boolean
printKPI=True                           # boolean

PARCELS_PER_EMPL=0.00                   # float
Local2Local=0.04                        # float
CS_cust_willingness=0.1                 # float - Willingess to SEND a parcel by CS
PARCELS_MAXLOAD=180                     # float
PARCELS_DROPTIME=120                    # float
PARCELS_SUCCESS_B2C=0.90                # float
PARCELS_SUCCESS_B2B=0.95                # float
PARCELS_GROWTHFREIGHT=1.0               # float

PARCELS_PER_HH_B2C=0.195                # float
PARCELS_M=20.8                          # float
PARCELS_DAYS=250                        # float
PARCELS_M_HHS=8.0                       # float
```
