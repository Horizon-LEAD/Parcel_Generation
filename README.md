# Parcel_Gen

_Parcel Generation model for the Living Lab of The Hague for the LEAD platform._

## Installation

The `requirements.txt` and `Pipenv` files are provided for the setup of an environment where the module can be installed. The package includes a `setup.py` file and it can be therefore installed with a `pip install .` when we are at the same working directory as the `setup.py` file. For testing purposes, one can also install the package in editable mode `pip install -e .`.

After the install is completed, an executable `parcelgen` will be available to the user.

Furthermore, a `Dockerfile` is provided so that the user can package the parcel generation model. To build the image the following command must be issued from the project's root directory:

```
docker build -t parcel-generation:latest .
```

## Usage

The executable's help message provides information on the parameters that are needed.

```
$ parcel-generation -h
usage: parcel-generation [-h] [-v] [--flog] [-e ENV] [--gui] SKIMTIME SKIMDISTANCE ZONES SEGS PARCELNODES CEP_SHARES EXTERNAL_ZONES OUTDIR

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
LABEL='default'
# boolean parameters
RUN_DEMAND_MODULE=true
CROWDSHIPPING_NETWORK=True
COMBINE_DELIVERY_PICKUP_TOUR=True
HYPERCONNECTED_NETWORK=FALSE
printKPI=True

# numeric parameters
PARCELS_PER_EMPL=0.00
Local2Local=0.04
# Willingess to SEND a parcel by CS
CS_cust_willingness=0.1
PARCELS_MAXLOAD=180
PARCELS_DROPTIME=120
PARCELS_SUCCESS_B2C=0.90
PARCELS_SUCCESS_B2B=0.95
PARCELS_GROWTHFREIGHT=1.0

PARCELS_PER_HH_B2C=0.195
PARCELS_M=20.8
PARCELS_DAYS=250
PARCELS_M_HHS=8.0

# string list parameters
Gemeenten_studyarea="Delft,Midden_Delfland,Rijswijk,sGravenhage,Leidschendam_Voorburg"
```

### Examples

In the following examples, it is assumed that the user has placed all necessary input files in the `sample-data/inputs` directory while making sure that the `sample-data/outputs` directory exists.

```
parcel-generation -vvv --env .env \
  sample-data/input/skimTijd_new_REF.mtx \
  sample-data/input/skimAfstand_new_REF.mtx \
  sample-data/input/Zones_v4.shp \
  sample-data/input/SEGS2020.csv \
  sample-data/input/parcelNodes_v2.shp \
  sample-data/input/CEPshares.csv \
  sample-data/input/SupCoordinatesID.csv \
  sample-data/output
```

and with docker run (from the project's root directory):

```
docker run --rm \
  -v $PWD/sample-data/input:/data/input \
  -v $PWD/sample-data/output:/data/output \
  --env-file .env \
  parcel-generation:latest \
  /data/input/skimTijd_new_REF.mtx \
  /data/input/skimAfstand_new_REF.mtx \
  /data/input/Zones_v4.shp \
  /data/input/SEGS2020.csv \
  /data/input/parcelNodes_v2.shp \
  /data/input/CEPshares.csv \
  /data/input/SupCoordinatesID.csv \
  /data/output/
```
