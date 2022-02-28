from ast import literal_eval

import pandas as pd
import numpy as np
import shapefile as shp
import array
import os.path

ENV_VARS = ["PARAMS_FILE", "SKIMTIME", "SKIMDISTANCE", "ZONES", "SEGS", "PARCELNODES", 
            "CEP_SHARES", "EXTERNAL_ZONES", "CONSOLIDATION_POTENTIAL", 
            "ZEZ_SCENARIO"]


def parse_params_file(path):
    """Parses the parameters file

    :param path: The parameters file path
    :type path: str
    :return: A dictionary with the parameters
    :rtype: dict
    """

    varDict = {}
    params_file = open(path)

    for line in params_file:
        if len(line.split('=')) > 1:
            key, value = line.split('=')
            if len(value.split(':')) > 1:
                value, dtype = value.split(':')
                if len(dtype.split('#')) > 1: dtype, comment = dtype.split('#')
                # Allow for spacebars around keys, values and dtypes
                while key[0] == ' ' or key[0] == '\t': key = key[1:]
                while key[-1] == ' ' or key[-1] == '\t': key = key[0:-1]
                while value[0] == ' ' or value[0] == '\t': value = value[1:]
                while value[-1] == ' ' or value[-1] == '\t': value = value[0:-1]
                while dtype[0] == ' ' or dtype[0] == '\t': dtype = dtype[1:]
                while dtype[-1] == ' ' or dtype[-1] == '\t': dtype = dtype[0:-1]
                dtype = dtype.replace('\n',"")
                # print(key, value, dtype)
                if dtype == 'string': varDict[key] = str(value)
                elif dtype == 'list': varDict[key] = literal_eval(value)
                elif dtype == 'int': varDict[key] = int(value)               
                elif dtype == 'float': varDict[key] = float(value)               
                elif dtype == 'bool': varDict[key] = eval(value)               
                elif dtype == 'variable': varDict[key] = globals()[value]
                elif dtype == 'eval': varDict[key] = eval(value)          

    return varDict


def parse_env_values(config):
    try:
        assert 'LABEL' in config
        assert os.path.exists(config['INPUTFOLDER'])
        assert os.path.exists(config['OUTPUTFOLDER'])

        if not os.path.isabs(config['INPUTFOLDER']):
            config['INPUTFOLDER'] = os.path.abspath(config['INPUTFOLDER'])
            print(f"WARNING: INPUTFOLDER not an absolute path - translating to: {config['INPUTFOLDER']}")
        if not os.path.isabs(config['OUTPUTFOLDER']):
            config['OUTPUTFOLDER'] = os.path.abspath(config['OUTPUTFOLDER'])
            print(f"WARNING: OUTPUTFOLDER not an absolute path - translating to: {config['OUTPUTFOLDER']}")

        for key in ENV_VARS:
            if key in ("LABEL", "INPUTFOLDER", "OUTPUTFOLDER"):
                continue

            config[key] = os.path.join(config['INPUTFOLDER'], config[key])
    except (AssertionError, TypeError, KeyError) as exc:
        raise AssertionError("Failed while parsing environment configuration") from exc
    
    return config.copy()


def get_traveltime(orig,dest,skim,nZones,timeFac):
    ''' Obtain the travel time [h] for orig to a destination zone. '''
    return skim[(orig-1)*nZones+(dest-1)] * timeFac / 3600


def get_distance(orig,dest,skim,nZones):
    ''' Obtain the distance [km] for orig to a destination zone. '''
    return skim[(orig-1)*nZones+(dest-1)] / 1000


def read_mtx(mtxfile):  
    '''
    Read a binary mtx-file (skimTijd and skimAfstand)
    '''
    mtxData = array.array('i')  # i for integer
    mtxData.fromfile(open(mtxfile, 'rb'), os.path.getsize(mtxfile) // mtxData.itemsize)
    
    # The number of zones is in the first byte
    mtxData = np.array(mtxData, dtype=int)[1:]
    
    return mtxData


def read_shape(shapePath, encoding='latin1', returnGeometry=False):
    '''
    Read the shapefile with zones (using pyshp --> import shapefile as shp)
    '''
    # Load the shape
    sf = shp.Reader(shapePath, encoding=encoding)
    records = sf.records()
    if returnGeometry:
        geometry = sf.__geo_interface__
        geometry = geometry['features']
        geometry = [geometry[i]['geometry'] for i in range(len(geometry))]
    fields = sf.fields
    sf.close()
    
    # Get information on the fields in the DBF
    columns  = [x[0] for x in fields[1:]]
    colTypes = [x[1:] for x in fields[1:]]
    nRecords = len(records)
    
    # Put all the data records into a NumPy array (much faster than Pandas DataFrame)
    shape = np.zeros((nRecords,len(columns)), dtype=object)
    for i in range(nRecords):
        shape[i,:] = records[i][0:]
    
    # Then put this into a Pandas DataFrame with the right headers and data types
    shape = pd.DataFrame(shape, columns=columns)
    for col in range(len(columns)):
        if colTypes[col][0] == 'C':
            shape[columns[col]] = shape[columns[col]].astype(str)
        else:
            shape.loc[pd.isna(shape[columns[col]]), columns[col]] = -99999
            if colTypes[col][-1] > 0:
                shape[columns[col]] = shape[columns[col]].astype(float)
            else:
                shape[columns[col]] = shape[columns[col]].astype(int)
    
    if returnGeometry:
        return (shape, geometry)
    else:
        return shape


def create_geojson(output_path, DataFrame, origin_x, origin_y, destination_x, destination_y)    :
    #----- GeoJSON ---
    # print('Writing GeoJSON...') 
    Ax = np.array(DataFrame[origin_x], dtype=str)
    Ay = np.array(DataFrame[origin_y], dtype=str)
    Bx = np.array(DataFrame[destination_x], dtype=str)
    By = np.array(DataFrame[destination_y], dtype=str)
    nTrips = len(DataFrame.index)
    
    with open(output_path, 'w') as geoFile:
        geoFile.write('{\n' + '"type": "FeatureCollection",\n' + '"features": [\n')
        for i in range(nTrips-1):
            outputStr = ""
            outputStr = outputStr + '{ "type": "Feature", "properties": '
            outputStr = outputStr + str(DataFrame.loc[i,:].to_dict()).replace("'",'"')
            outputStr = outputStr + ', "geometry": { "type": "LineString", "coordinates": [ [ '
            outputStr = outputStr + Ax[i] + ', ' + Ay[i] + ' ], [ '
            outputStr = outputStr + Bx[i] + ', ' + By[i] + ' ] ] } },\n'
            geoFile.write(outputStr)
                
        # Bij de laatste feature moet er geen komma aan het einde
        i += 1
        outputStr = ""
        outputStr = outputStr + '{ "type": "Feature", "properties": '
        outputStr = outputStr + str(DataFrame.loc[i,:].to_dict()).replace("'",'"')
        outputStr = outputStr + ', "geometry": { "type": "LineString", "coordinates": [ [ '
        outputStr = outputStr + Ax[i] + ', ' + Ay[i] + ' ], [ '
        outputStr = outputStr + Bx[i] + ', ' + By[i] + ' ] ] } }\n'
        geoFile.write(outputStr)
        geoFile.write(']\n')
        geoFile.write('}')
