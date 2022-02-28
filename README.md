# Parcel_Gen
 
_Parcel Generation model for the Living Lab of The Hague for the LEAD platform._

## Installation

## Usage

A python environment with the following packages is required:
```
networkx==2.6.3
pandas==1.3.4
pyshp==2.1.3
tk==0.1.0
python-dotenv==0.19.2
```

A `Pipenv` file is also provided for environment setup. 

To execute the model initially the input data set must be located in a specific directory.
The input data are then set to an environment file (`.env`) that is provided to the command line execution of the model.

Then the `parcel_gen` module can be installed and executed as:
```
cd <dir>/Parcel_Generation  # go to the project's root folder
pip install -e .            # install the module in editable mode
parcelgen -e .env           # the executable is created and can be run
```
