"""An environment variables controller
"""

from logging import getLogger
from json import loads, JSONDecodeError


BOOL_VALUES = ('true', 't', 'on', '1', 'false', 'f', 'off', '0', "")
BOOL_TRUE_VALUES = ('true', 't', 'on', '1')

PARAMS_STR = ["LABEL"]
PARAMS_BOOL = ["RUN_DEMAND_MODULE", "CROWDSHIPPING_NETWORK", "COMBINE_DELIVERY_PICKUP_TOUR",
               "HYPERCONNECTED_NETWORK", "printKPI"]
PARAMS_NUM = ["PARCELS_PER_EMPL", "Local2Local", "CS_cust_willingness",
              "PARCELS_MAXLOAD", "PARCELS_DROPTIME", "PARCELS_SUCCESS_B2C",
              "PARCELS_SUCCESS_B2B", "PARCELS_GROWTHFREIGHT", "PARCELS_PER_HH_B2C",
              "PARCELS_M", "PARCELS_DAYS", "PARCELS_M_HHS", "PL_ZonalDemand"]
PARAMS_LIST_STR = ["Gemeenten_studyarea"] 
PARAMS_LIST_BOOL = []
PARAMS_LIST_NUM = ["parcelLockers_zones"]
PARAMS_JSON = []

logger = getLogger("parcelgen.envctl")


def to_bool(value):
    """Translates a string to boolean value.

    :param value: The input string
    :type value: str
    :raises ValueError: raises value error if the string is not recognized.
    :return: The translated boolean value
    :rtype: bool
    """
    val = str(value).lower().strip()
    if val not in BOOL_VALUES:
        raise ValueError(f'error: {value} is not a recognized boolean value {BOOL_VALUES}')
    if val in BOOL_TRUE_VALUES:
        return True
    return False


def parse_env_values(env):
    """Parses environment values.

    :param env: The environment dictionary
    :type env: dict
    :raises KeyError: If a required key is missing
    :raises ValueError: If the value of the key is invalid
    :return: The configuration dictionary
    :rtype: dict
    """
    config_env = {}
    try:
        for key in PARAMS_STR:
            config_env[key] = env[key]
        for key in PARAMS_BOOL:
            config_env[key] = to_bool(env[key])
        for key in PARAMS_NUM:
            config_env[key] = float(env[key])
        for key in PARAMS_LIST_STR:
            config_env[key] = [] if env[key] == '' else env[key].split(',')
        for key in PARAMS_LIST_BOOL:
            config_env[key] = [] if env[key] == '' else list(map(to_bool, env[key].split(',')))
        for key in PARAMS_LIST_NUM:
            config_env[key] = [] if env[key] == '' else list(map(float, env[key].split(',')))
        for key in PARAMS_JSON:
            config_env[key] = {} if env[key] == '' else loads(env[key])
    except KeyError as exc:
        raise KeyError("Failed while parsing environment configuration") from exc
    except JSONDecodeError as exc:
        raise ValueError("Failed while parsing JSON environment configuration") from exc
    except ValueError as exc:
        raise ValueError("Failed while parsing environment configuration") from exc

    # specific to Parcel Generation
    config_env["PARCELS_PER_HH_C2C"] = config_env["PARCELS_M"] / config_env["PARCELS_DAYS"] \
        / config_env["PARCELS_M_HHS"]
    config_env["PARCELS_PER_HH"] = config_env["PARCELS_PER_HH_C2C"] + \
        config_env['PARCELS_PER_HH_B2C']

    return config_env
