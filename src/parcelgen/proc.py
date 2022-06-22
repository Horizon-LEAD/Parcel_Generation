""" ParcelGen processing module
"""

import json
from os.path import join
from time import time
from logging import getLogger

import pandas as pd
import numpy as np

from .utils import read_shape, read_mtx


logger = getLogger("parcelgen.proc")


def run_model(cfg, root=None):
    """ Start the parcel generation simulation.

    :param cfg: The configuration dictionary
    :type cfg: dict
    :param root: ParcelGenUI instance in case gui flag is enabled, defaults to None
    :type root: ParcelGenUI, optional
    :return: Exit codes list
    :rtype: list
    """
    start_time = time()

    if root:
        root.progressBar['value'] = 0

    outdir = cfg['OUTDIR']
    label  = cfg['LABEL']

    # Import data
    logger.info('Importing data...')

    zones = read_shape(cfg['ZONES'])
    zones = pd.DataFrame(zones).sort_values('AREANR')
    zones.index = zones['AREANR']

    sup_coordinates = pd.read_csv(cfg['EXTERNAL_ZONES'], sep=',')
    sup_coordinates.index = sup_coordinates['AREANR']

    zones_x = {}
    zones_y = {}
    for areanr in zones.index:
        zones_x[areanr] = zones.at[areanr, 'X']
        zones_y[areanr] = zones.at[areanr, 'Y']
    for areanr in sup_coordinates.index:
        zones_x[areanr] = sup_coordinates.at[areanr, 'Xcoor']
        zones_y[areanr] = sup_coordinates.at[areanr, 'Ycoor']

    n_int_zones = len(zones)
    n_sup_zones = 43                    # FIXME: constant enough ? Maybe an arg ?
    zone_dict = dict(np.transpose(np.vstack( (np.arange(1, n_int_zones+1), zones['AREANR']) )))
    zone_dict = {int(a):int(b) for a,b in zone_dict.items()}
    for i in range(n_sup_zones):
        zone_dict[n_int_zones+i+1] = 99999900 + i + 1
    inv_zone_dict = dict((v, k) for k, v in zone_dict.items())

    segs = pd.read_csv(cfg['SEGS'])
    segs.index = segs['zone']

    parcel_nodes, coords = read_shape(cfg['PARCELNODES'], return_geometry=True)
    parcel_nodes['X'] = [coords[i]['coordinates'][0] for i in range(len(coords))]
    parcel_nodes['Y'] = [coords[i]['coordinates'][1] for i in range(len(coords))]
    parcel_nodes.index = parcel_nodes['id'].astype(int)
    parcel_nodes = parcel_nodes.sort_index()
    n_parcel_nodes = len(parcel_nodes)

    cep_shares = pd.read_csv(cfg['CEP_SHARES'], index_col=0)
    cep_list   = np.unique(parcel_nodes['CEP'])
    cep_nodes = [np.where(parcel_nodes['CEP']==str(cep))[0] for cep in cep_list]
    cep_node_dict = {}
    for cep_no, cep in enumerate(cep_list):
        cep_node_dict[cep] = cep_nodes[cep_no]

    # Get skim data and make parcel skim
    skim_trav_time = read_mtx(cfg['SKIMTIME'])
    n_zones   = int(len(skim_trav_time)**0.5)
    parcel_skim = np.zeros((n_zones, n_parcel_nodes))

    # Skim with travel times between parcel nodes and all other zones
    i = 0
    for parcel_node_zone in parcel_nodes['AREANR']:
        orig = inv_zone_dict[parcel_node_zone]
        dest = 1 + np.arange(n_zones)
        parcel_skim[:,i] = np.round( (skim_trav_time[(orig-1)*n_zones+(dest-1)] / 3600),4)
        i += 1

    # Generate parcels each zone based on households and select a parcel node for each parcel
    logger.info('Generating parcels...')

    # Calculate number of parcels per zone based on number of households and
    # total number of parcels on an average day
    zones = zones[zones['GEMEENTEN'].isin(cfg['Gemeenten_studyarea'])]
    zones['parcels']  = (segs['1: woningen'] * cfg['PARCELS_PER_HH']   / \
        cfg['PARCELS_SUCCESS_B2C'])
    zones['parcels'] += (segs['9: arbeidspl_totaal'] * cfg['PARCELS_PER_EMPL'] / \
        cfg['PARCELS_SUCCESS_B2B'])
    zones['parcels']  = np.array(np.round(zones['parcels'],0), dtype=int)

    # Spread over couriers based on market shares
    for cep in cep_list:
        zones['parcels_' + str(cep)] = np.round(cep_shares['ShareTotal'][cep] * zones['parcels'], 0)
        zones['parcels_' + str(cep)] = zones['parcels_' + str(cep)].astype(int)

    # Total number of parcels per courier
    n_parcels  = int(zones[["parcels_" + str(cep) for cep in cep_list]].sum().sum())

    # Put parcel demand in Numpy array (faster indexing)
    cols    = ['Parcel_ID', 'O_zone', 'D_zone', 'DepotNumber']
    parcels = np.zeros((n_parcels, len(cols)), dtype=int)
    parcels_cep = np.array(['' for _ in range(n_parcels)], dtype=object)

    # Now determine for each zone and courier from which depot the parcels are delivered
    count = 0
    for zone_id in zones['AREANR'] :

        if zones['parcels'][zone_id] > 0: # Go to next zone if no parcels are delivered here

            for cep in cep_list:
                # Select dc based on min in parcelSkim
                parcel_node_index = cep_node_dict[cep][parcel_skim[inv_zone_dict[zone_id]-1,
                                                                   cep_node_dict[cep]].argmin()]

                # Fill allParcels with parcels, zone after zone.
                # Parcels consist of ID, D and O zone and parcel node number
                # in ongoing df from index count-1 the next x=no. of parcels rows,
                # fill the cell in the column Parcel_ID with a number
                zone_idx = zones.loc[zone_id, 'parcels_' + str(cep)]
                parcels[count:count+zone_idx, 0] = np.arange(count+1, count+1+zone_idx, dtype=int)
                parcels[count:count+zone_idx, 1] = parcel_nodes['AREANR'][parcel_node_index+1]
                parcels[count:count+zone_idx, 2] = zone_id
                parcels[count:count+zone_idx, 3] = parcel_node_index + 1
                parcels_cep[count:count+zone_idx] = cep

                count += zones['parcels_' + str(cep)][zone_id]

    # Put the parcel demand data back in a DataFrame
    parcels = pd.DataFrame(parcels, columns=cols)
    parcels['CEP'] = parcels_cep

    # Default vehicle type for parcel deliveries: vans
    parcels['VEHTYPE'] = 7

    # Rerouting through UCCs in the UCC-scenario
    if label == 'UCC':
        vt_names_ucc = ['LEVV','Moped','Van','Truck','TractorTrailer',
                        'WasteCollection','SpecialConstruction']
        n_log_seg = 8

        # Logistic segment is 6: parcels
        log_seg = 6

        # Write the REF parcel demand
        out_parcel_demand_ref = join(outdir, "ParcelDemandUCC.csv")
        logger.info("Writing parcels to %s", out_parcel_demand_ref)
        parcels.to_csv(out_parcel_demand_ref, index=False)

        # Consolidation potential per logistic segment (for UCC scenario)
        prob_consolidation = np.array(pd.read_csv(cfg['CONSOLIDATION_POTENTIAL'],
                                                 index_col='Segment'))

        # Vehicle/combustion shares (for UCC scenario)
        shares_ucc  = pd.read_csv(cfg['ZEZ_SCENARIO'], index_col='Segment')

        # Assume no consolidation potential and vehicle type switch for dangerous goods
        shares_ucc = np.array(shares_ucc)[:-1, :-1]

        # Only vehicle shares (summed up combustion types)
        shares_veh_ucc = np.zeros((n_log_seg-1, len(vt_names_ucc)))
        for i_ls in range(n_log_seg-1):
            shares_veh_ucc[i_ls, 0] = np.sum(shares_ucc[i_ls, 0:5])
            shares_veh_ucc[i_ls, 1] = np.sum(shares_ucc[i_ls, 5:10])
            shares_veh_ucc[i_ls, 2] = np.sum(shares_ucc[i_ls, 10:15])
            shares_veh_ucc[i_ls, 3] = np.sum(shares_ucc[i_ls, 15:20])
            shares_veh_ucc[i_ls, 4] = np.sum(shares_ucc[i_ls, 20:25])
            shares_veh_ucc[i_ls, 5] = np.sum(shares_ucc[i_ls, 25:30])
            shares_veh_ucc[i_ls, 6] = np.sum(shares_ucc[i_ls, 30:35])
            shares_veh_ucc[i_ls, :] = np.cumsum(shares_veh_ucc[i_ls, :]) / \
                np.sum(shares_veh_ucc[i_ls, :])

        # Couple these vehicle types to Harmony vehicle types
        veh_ucc_to_veh = {0:8, 1:9, 2:7, 3:1, 4:5, 5:6, 6:6}

        logger.info('Redirecting parcels via UCC...')

        parcels['FROM_UCC'] = 0
        parcels['TO_UCC'  ] = 0

        dest_zones = np.array(parcels['D_zone'].astype(int))
        depot_numbers = np.array(parcels['DepotNumber'].astype(int))
        where_dest_zez = np.where(
            (zones['ZEZ'][dest_zones]==1) & \
                (prob_consolidation[log_seg][0] > np.random.rand(len(parcels))))[0]

        new_parcels = np.zeros(parcels.shape, dtype=object)

        count = 0

        for i in where_dest_zez:
            true_dest = dest_zones[i]

            # Redirect to UCC
            parcels.at[i,'D_zone'] = zones['UCC_zone'][true_dest]
            parcels.at[i,'TO_UCC'] = 1

            # Add parcel set to ZEZ from UCC
            new_parcels[count, 1] = zones['UCC_zone'][true_dest]      # Origin
            new_parcels[count, 2] = true_dest                         # Destination
            new_parcels[count, 3] = depot_numbers[i]                  # Depot ID
            new_parcels[count, 4] = parcels_cep[i]                    # Courier name
            new_parcels[count, 5] = veh_ucc_to_veh[
                    np.where(shares_veh_ucc[log_seg,:]>np.random.rand())[0][0]
            ] # Vehicle type
            new_parcels[count, 6] = 1                    # From UCC
            new_parcels[count, 7] = 0                    # To UCC

            count += 1

        new_parcels = pd.DataFrame(new_parcels)
        new_parcels.columns = parcels.columns
        new_parcels = new_parcels.iloc[np.arange(count), :]

        dtypes = {'Parcel_ID': int, 'O_zone': int, 'D_zone': int,   'DepotNumber': int,
                  'CEP': str, 'VEHTYPE': int, 'FROM_UCC': int, 'TO_UCC': int}
        for key, v_type in dtypes.items():
            new_parcels[key] = new_parcels[key].astype(v_type)

        parcels = parcels.append(new_parcels)
        parcels.index = np.arange(len(parcels))
        parcels['Parcel_ID'] = np.arange(1, len(parcels)+1)

        n_parcels = len(parcels)

    # Prepare output
    out_parcel_demand = join(outdir, "ParcelDemand.csv")
    logger.info("Writing parcels CSV to %s", out_parcel_demand)
    parcels.to_csv(out_parcel_demand, index=False)

    # Write KPIs as Json
    # FIXME: iteration will never run - fix KPIs population to dict -> JSON
    logger.info("Populating KPIs")
    kpis = {}
    kpis["Number Of Parcels"] = len(parcels)

    # For some reason, json doesn't like np.int or floats
    # for index, key in enumerate(kpis):
    #     # print(key)
    #     if type(kpis[key]) == 'dict':
    #         for i, k in enumerate (key):
    #             print(k)
    #             if type(key[k]) == 'dict':
    #                 for j, l in enumerate(k):
    #                     try:
    #                         val = k[l].item()
    #                         k[l] = val
    #                         key[k] = k
    #                     except:
    #                         a=1
    #             else:
    #                 try:
    #                     val = key[k].item()
    #                     key[k] = val
    #                     kpis[key] = key
    #                 except:
    #                     a=1
    #     else:
    #         try:
    #             val = kpis[key].item()
    #             kpis[key] = val
    #         except:
    #             a=1

    out_kpis_json = join(outdir, "kpis.json")
    logger.info("Writing KPIs JSON file to %s", out_kpis_json)
    with open(out_kpis_json, "w", encoding='utf_8') as fp_kpis:
        json.dump(kpis, fp_kpis, indent = 2)

    if cfg['printKPI'] :
        logger.info(json.dumps(kpis, indent = 2))

    totaltime = round(time() - start_time, 2)
    logger.info("Total runtime: %s seconds", totaltime)

    if root:
        root.update_statusbar("Parcel Demand: Done")
        root.progressBar['value'] = 100

        # 0 means no errors in execution
        root.returnInfo = [0, [0, 0]]

        return root.returnInfo

    return [0, [0, 0]]
