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
KPIs = {}


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

    # ---------------------------- Import data --------------------------------
    logger.info('Importing data...')

    zones = read_shape(cfg['ZONES'])
    zones = pd.DataFrame(zones).sort_values('AREANR')
    zones.index = zones['AREANR']

    sup_coordinates = pd.read_csv(cfg['EXTERNAL_ZONES'], sep=',')
    sup_coordinates.index = sup_coordinates['AREANR']

    zonesX = {}
    zonesY = {}
    for areanr in zones.index:
        zonesX[areanr] = zones.at[areanr, 'X']
        zonesY[areanr] = zones.at[areanr, 'Y']
    for areanr in sup_coordinates.index:
        zonesX[areanr] = sup_coordinates.at[areanr, 'Xcoor']
        zonesY[areanr] = sup_coordinates.at[areanr, 'Ycoor']

    nIntZones = len(zones)
    nSupZones = 43
    zoneDict  = dict(np.transpose(np.vstack( (np.arange(1,nIntZones+1), zones['AREANR']) )))
    zoneDict  = {int(a):int(b) for a,b in zoneDict.items()}
    for i in range(nSupZones):
        zoneDict[nIntZones+i+1] = 99999900 + i + 1
    invZoneDict = dict((v, k) for k, v in zoneDict.items())

    segs              = pd.read_csv(cfg['SEGS'])
    segs.index        = segs['zone']

    parcelNodes, coords = read_shape(cfg['PARCELNODES'], returnGeometry=True)
    parcelNodes['X']    = [coords[i]['coordinates'][0] for i in range(len(coords))]
    parcelNodes['Y']    = [coords[i]['coordinates'][1] for i in range(len(coords))]
    parcelNodes.index   = parcelNodes['id'].astype(int)
    parcelNodes         = parcelNodes.sort_index()
    nParcelNodes        = len(parcelNodes)

    cepShares = pd.read_csv(cfg['CEP_SHARES'], index_col=0)
    cepList   = np.unique(parcelNodes['CEP'])
    cepNodes = [np.where(parcelNodes['CEP']==str(cep))[0] for cep in cepList]
    cepNodeDict = {}
    for cepNo in range(len(cepList)):
        cepNodeDict[cepList[cepNo]] = cepNodes[cepNo]


    # ------------------ Get skim data and make parcel skim --------------------
    skimTravTime = read_mtx(cfg['SKIMTIME'])
    nZones   = int(len(skimTravTime)**0.5)
    parcelSkim = np.zeros((nZones, nParcelNodes))

    # Skim with travel times between parcel nodes and all other zones
    i = 0
    for parcelNodeZone in parcelNodes['AREANR']:
        orig = invZoneDict[parcelNodeZone]
        dest = 1 + np.arange(nZones)
        parcelSkim[:,i] = np.round( (skimTravTime[(orig-1)*nZones+(dest-1)] / 3600),4)
        i += 1


    # ---- Generate parcels each zone based on households and select a parcel node for each parcel -----
    logger.info('Generating parcels...')

    # Calculate number of parcels per zone based on number of households and
    # total number of parcels on an average day
    zones['parcels']  = (segs['1: woningen'        ] * cfg['PARCELS_PER_HH']   / cfg['PARCELS_SUCCESS_B2C'])
    zones['parcels'] += (segs['9: arbeidspl_totaal'] * cfg['PARCELS_PER_EMPL'] / cfg['PARCELS_SUCCESS_B2B'])
    zones['parcels']  = np.array(np.round(zones['parcels'],0), dtype=int)

    # Spread over couriers based on market shares
    for cep in cepList:
        zones['parcels_' + str(cep)] = np.round(cepShares['ShareTotal'][cep] * zones['parcels'], 0)
        zones['parcels_' + str(cep)] = zones['parcels_' + str(cep)].astype(int)

    # Total number of parcels per courier
    nParcels  = int(zones[["parcels_"+str(cep) for cep in cepList]].sum().sum())

    # Put parcel demand in Numpy array (faster indexing)
    cols    = ['Parcel_ID', 'O_zone', 'D_zone', 'DepotNumber']
    parcels = np.zeros((nParcels,len(cols)), dtype=int)
    parcelsCep = np.array(['' for i in range(nParcels)], dtype=object)

    # Now determine for each zone and courier from which depot the parcels are delivered
    count = 0
    for zoneID in zones['AREANR'] :

        if zones['parcels'][zoneID] > 0: # Go to next zone if no parcels are delivered here

            for cep in cepList:
                # Select dc based on min in parcelSkim
                parcelNodeIndex = cepNodeDict[cep][parcelSkim[invZoneDict[zoneID]-1,cepNodeDict[cep]].argmin()]

                # Fill allParcels with parcels, zone after zone. Parcels consist of ID, D and O zone and parcel node number
                # in ongoing df from index count-1 the next x=no. of parcels rows, fill the cell in the column Parcel_ID with a number
                n = zones.loc[zoneID,'parcels_' + str(cep)]
                parcels[count:count+n,0]  = np.arange(count+1, count+1+n,dtype=int)
                parcels[count:count+n,1]  = parcelNodes['AREANR'][parcelNodeIndex+1]
                parcels[count:count+n,2]  = zoneID
                parcels[count:count+n,3]  = parcelNodeIndex + 1
                parcelsCep[count:count+n] = cep

                count += zones['parcels_' + str(cep)][zoneID]

    # Put the parcel demand data back in a DataFrame
    parcels = pd.DataFrame(parcels, columns=cols)
    parcels['CEP'] = parcelsCep

    # Default vehicle type for parcel deliveries: vans
    parcels['VEHTYPE'] = 7

    # Rerouting through UCCs in the UCC-scenario
    if label == 'UCC':

        vtNamesUCC = ['LEVV','Moped','Van','Truck','TractorTrailer','WasteCollection','SpecialConstruction']
        nLogSeg = 8

        # Logistic segment is 6: parcels
        ls = 6

        # Write the REF parcel demand
        out_parcel_demand_ref = join(outdir, "ParcelDemand_REF.csv")
        logger.info(f"Writing parcels to %s", out_parcel_demand_ref),
        parcels.to_csv(out_parcel_demand_ref, index=False)

        # Consolidation potential per logistic segment (for UCC scenario)
        probConsolidation = np.array(pd.read_csv(cfg['CONSOLIDATION_POTENTIAL'], index_col='Segment'))

        # Vehicle/combustion shares (for UCC scenario)
        sharesUCC  = pd.read_csv(cfg['ZEZ_SCENARIO'], index_col='Segment')

        # Assume no consolidation potential and vehicle type switch for dangerous goods
        sharesUCC = np.array(sharesUCC)[:-1,:-1]

        # Only vehicle shares (summed up combustion types)
        sharesVehUCC = np.zeros((nLogSeg-1,len(vtNamesUCC)))
        for ls in range(nLogSeg-1):
            sharesVehUCC[ls,0] = np.sum(sharesUCC[ls,0:5])
            sharesVehUCC[ls,1] = np.sum(sharesUCC[ls,5:10])
            sharesVehUCC[ls,2] = np.sum(sharesUCC[ls,10:15])
            sharesVehUCC[ls,3] = np.sum(sharesUCC[ls,15:20])
            sharesVehUCC[ls,4] = np.sum(sharesUCC[ls,20:25])
            sharesVehUCC[ls,5] = np.sum(sharesUCC[ls,25:30])
            sharesVehUCC[ls,6] = np.sum(sharesUCC[ls,30:35])
            sharesVehUCC[ls,:] = np.cumsum(sharesVehUCC[ls,:]) / np.sum(sharesVehUCC[ls,:])

        # Couple these vehicle types to Harmony vehicle types
        vehUccToVeh = {0:8, 1:9, 2:7, 3:1, 4:5, 5:6, 6:6}

        logger.info('Redirecting parcels via UCC...')

        parcels['FROM_UCC'] = 0
        parcels['TO_UCC'  ] = 0

        destZones    = np.array(parcels['D_zone'].astype(int))
        depotNumbers = np.array(parcels['DepotNumber'].astype(int))
        whereDestZEZ = np.where((zones['ZEZ'][destZones]==1) & (probConsolidation[ls][0] > np.random.rand(len(parcels))))[0]

        newParcels = np.zeros(parcels.shape, dtype=object)

        count = 0

        for i in whereDestZEZ:

            trueDest = destZones[i]

            # Redirect to UCC
            parcels.at[i,'D_zone'] = zones['UCC_zone'][trueDest]
            parcels.at[i,'TO_UCC'] = 1

            # Add parcel set to ZEZ from UCC
            newParcels[count, 1] = zones['UCC_zone'][trueDest]  # Origin
            newParcels[count, 2] = trueDest             # Destination
            newParcels[count, 3] = depotNumbers[i]      # Depot ID
            newParcels[count, 4] = parcelsCep[i]        # Courier name
            newParcels[count, 5] = vehUccToVeh[
                    np.where(sharesVehUCC[ls,:]>np.random.rand())[0][0]
            ] # Vehicle type
            newParcels[count, 6] = 1                    # From UCC
            newParcels[count, 7] = 0                    # To UCC

            count += 1

        newParcels = pd.DataFrame(newParcels)
        newParcels.columns = parcels.columns
        newParcels = newParcels.iloc[np.arange(count),:]

        dtypes = {'Parcel_ID':int, 'O_zone':int,  'D_zone':int,   'DepotNumber':int, \
                    'CEP':str,       'VEHTYPE':int, 'FROM_UCC':int, 'TO_UCC':int}
        for col in dtypes.keys():
            newParcels[col] = newParcels[col].astype(dtypes[col])

        parcels = parcels.append(newParcels)
        parcels.index = np.arange(len(parcels))
        parcels['Parcel_ID'] = np.arange(1,len(parcels)+1)

        nParcels = len(parcels)

    # ------------------------- Prepare output --------------------------------
    out_parcel_demand = join(outdir, "ParcelDemand.csv")
    logger.info("Writing parcels CSV to %s", out_parcel_demand)
    parcels.to_csv(out_parcel_demand, index=False)

    # # Aggregate to number of parcels per zone and export to geojson
    # logger.info("Writing parcels GeoJSON to %s", join(outdir, "ParcelDemand.geojson"))
    # if label == 'UCC':
    #     parcelsShape = pd.pivot_table(parcels, values=['Parcel_ID'], index=["DepotNumber", 'CEP','D_zone', 'O_zone', 'VEHTYPE', 'FROM_UCC', 'TO_UCC'],\
    #                                   aggfunc = {'DepotNumber': np.mean, 'CEP':     'first',  'O_zone': np.mean, 'D_zone': np.mean, 'Parcel_ID': 'count', \
    #                                              'VEHTYPE':     np.mean, 'FROM_UCC': np.mean, 'TO_UCC': np.mean})
    #     parcelsShape = parcelsShape.rename(columns={'Parcel_ID':'Parcels'})
    #     parcelsShape = parcelsShape.set_index(np.arange(len(parcelsShape)))
    #     parcelsShape = parcelsShape.reindex(columns=[ 'O_zone','D_zone', 'Parcels', 'DepotNumber', 'CEP','VEHTYPE', 'FROM_UCC', 'TO_UCC'])
    #     parcelsShape = parcelsShape.astype({'DepotNumber': int, 'O_zone': int, 'D_zone': int, 'Parcels': int, 'VEHTYPE': int, 'FROM_UCC': int, 'TO_UCC': int})

    # else:
    #     parcelsShape = pd.pivot_table(parcels, values=['Parcel_ID'], index=["DepotNumber", 'CEP', 'D_zone', 'O_zone'],\
    #                                   aggfunc = {'DepotNumber': np.mean, 'CEP':'first', 'O_zone': np.mean, 'D_zone': np.mean, 'Parcel_ID': 'count'})
    #     parcelsShape = parcelsShape.rename(columns={'Parcel_ID':'Parcels'})
    #     parcelsShape = parcelsShape.set_index(np.arange(len(parcelsShape)))
    #     parcelsShape = parcelsShape.reindex(columns=[ 'O_zone','D_zone', 'Parcels', 'DepotNumber', 'CEP'])
    #     parcelsShape = parcelsShape.astype({'DepotNumber': int, 'O_zone': int, 'D_zone': int, 'Parcels': int})


    # # Initialize arrays with coordinates
    # Ax = np.zeros(len(parcelsShape), dtype=int)
    # Ay = np.zeros(len(parcelsShape), dtype=int)
    # Bx = np.zeros(len(parcelsShape), dtype=int)
    # By = np.zeros(len(parcelsShape), dtype=int)

    # # Determine coordinates of LineString for each trip
    # depotIDs = np.array(parcelsShape['DepotNumber'])
    # for i in parcelsShape.index:
    #     if label == 'UCC' and parcelsShape.at[i, 'FROM_UCC'] == 1:
    #             Ax[i] = zonesX[parcelsShape['O_zone'][i]]
    #             Ay[i] = zonesY[parcelsShape['O_zone'][i]]
    #             Bx[i] = zonesX[parcelsShape['D_zone'][i]]
    #             By[i] = zonesY[parcelsShape['D_zone'][i]]
    #     else:
    #         Ax[i] = parcelNodes['X'][depotIDs[i]]
    #         Ay[i] = parcelNodes['Y'][depotIDs[i]]
    #         Bx[i] = zonesX[parcelsShape['D_zone'][i]]
    #         By[i] = zonesY[parcelsShape['D_zone'][i]]

    # Ax = np.array(Ax, dtype=str)
    # Ay = np.array(Ay, dtype=str)
    # Bx = np.array(Bx, dtype=str)
    # By = np.array(By, dtype=str)
    # nRecords = len(parcelsShape)

    # with open(join(outdir, "ParcelDemand.geojson"), 'w', encoding = 'utf_8') as fp_geo:
    #     fp_geo.write('{\n' + '"type": "FeatureCollection",\n' + '"features": [\n')
    #     for i in range(nRecords-1):
    #         outputStr = ""
    #         outputStr = outputStr + '{ "type": "Feature", "properties": '
    #         outputStr = outputStr + str(parcelsShape.loc[i,:].to_dict()).replace("'",'"')
    #         outputStr = outputStr + ', "geometry": { "type": "LineString", "coordinates": [ [ '
    #         outputStr = outputStr + Ax[i] + ', ' + Ay[i] + ' ], [ '
    #         outputStr = outputStr + Bx[i] + ', ' + By[i] + ' ] ] } },\n'
    #         fp_geo.write(outputStr)
    #         if i%int(nRecords/10) == 0:
    #             print('\t' + str(int(round((i / nRecords)*100, 0))) + '%', end='\r')

    #     # Bij de laatste feature moet er geen komma aan het einde
    #     i += 1
    #     outputStr = ""
    #     outputStr = outputStr + '{ "type": "Feature", "properties": '
    #     outputStr = outputStr + str(parcelsShape.loc[i,:].to_dict()).replace("'",'"')
    #     outputStr = outputStr + ', "geometry": { "type": "LineString", "coordinates": [ [ '
    #     outputStr = outputStr + Ax[i] + ', ' + Ay[i] + ' ], [ '
    #     outputStr = outputStr + Bx[i] + ', ' + By[i] + ' ] ] } }\n'
    #     fp_geo.write(outputStr)
    #     fp_geo.write(']\n')
    #     fp_geo.write('}')

    # Write KPIs as Json
    out_kpis_json = join(outdir, "KPI.json")
    logger.info("Writing KPIs JSON file to %s", out_kpis_json)
    # For some reason, json doesn't like np.int or floats
    for index, key in enumerate(KPIs):
        # print(key)
        if type(KPIs[key]) == 'dict':
            for i,k in enumerate (key):
                print(k)
                if type(key[k]) == 'dict':
                    for j,l in enumerate(k):
                        try:
                            val = k[l].item()
                            k[l] = val
                            key[k] = k
                        except:
                            a=1
                else:
                    try:
                        val = key[k].item()
                        key[k] = val
                        KPIs[key] = key
                    except:
                        a=1
        else:
            try:
                val = KPIs[key].item()
                KPIs[key] = val
            except:
                a=1

    with open(out_kpis_json, "w", encoding='utf_8') as fp_kpis:
        json.dump(KPIs, fp_kpis, indent = 2)

    if cfg['printKPI'] :
        logger.info(json.dumps(KPIs, indent = 2))

    totaltime = round(time() - start_time, 2)
    logger.info("Total runtime: %s seconds", totaltime)

    if root:
        root.update_statusbar("Parcel Demand: Done")
        root.progressBar['value'] = 100

        # 0 means no errors in execution
        root.returnInfo = [0, [0, 0]]

        return root.returnInfo

    else:
        return [0, [0, 0]]


    # except Exception as exc:
    #     print(exc)

    #     log_file.write(str(sys.exc_info()[0])), log_file.write("\n")
    #     log_file.write(str(traceback.format_exc())), log_file.write("\n")
    #     log_file.write("Execution failed!")
    #     log_file.close()

    #     if root != '':
    #         # Use this information to display as error message in GUI
    #         root.returnInfo = [1, [sys.exc_info()[0], traceback.format_exc()]]

    #         if __name__ == '__main__':
    #             root.update_statusbar("Parcel Demand: Execution failed!")
    #             errorMessage = 'Execution failed!\n\n' + str(root.returnInfo[1][0]) + '\n\n' + str(root.returnInfo[1][1])
    #             root.error_screen(text=errorMessage, size=[900,350])

    #         else:
    #             return root.returnInfo
    #     else:
    #         return [1, [sys.exc_info()[0], traceback.format_exc()]]
