import os
os.chdir('/home/mingke.li/expOct_vege/')

###########################################################
#### DGGS modeling -- extract values with interpolation ###
###########################################################

import rasterio
import geopandas
import pandas
import numpy
import pyRserve
import shapely
from scipy import interpolate
import warnings
import time

shapely.speedups.enable()
conn = pyRserve.connect()
warnings.simplefilter('error', RuntimeWarning) 
start_time = time.time()

## construct a look-up table, storing resolution and corresponding cell size and vertical resolution
res_list = [16,17,18,19,20,21,22,23,24,25,26,27,28,29]
cell_size_list = [0.005,0.003,0.001,0.0009,0.0008,0.0006,0.0003,0.0002,0.0001,0.00006,0.00003,0.00002,0.00001,0.000005]
vertical_res_list = [0,0,0,1,1,2,2,3,3,4,4,5,5,6]
# convert to a pandas dataframe with resolution levels as index
look_up = pandas.DataFrame({'res': res_list, 'cell_size': cell_size_list, 'verti_res': vertical_res_list}, index = res_list)

## Prepare HRDEM_extent polygons
HRDEM_extent = geopandas.GeoDataFrame.from_file('Data/Projects_Footprints_dissolved.shp')
HRDEM_extent = HRDEM_extent.to_crs("EPSG:4617") # NAD83 CSRS

## Read DEMs -- CDEM + HRDEM
CDEM_TIF = rasterio.open('Data/CDEM_cgvd2013.tif')
CDEM_pixelSizeX = abs(CDEM_TIF.transform[0])
CDEM_pixelSizeY = abs(CDEM_TIF.transform[4])

HRDEM_TIF = rasterio.open('Data/HRDEM_mosaic.tif')
HRDEM_pixelSizeX = abs(HRDEM_TIF.transform[0])
HRDEM_pixelSizeY = abs(HRDEM_TIF.transform[4])

## Define the main funcitons  

# define a function to convert geographic lat/lon to cell centroid position
dggridR_import_script = '''library(dggridR)'''
conn.eval(dggridR_import_script)

conn.voidEval('''
geo_to_centroid <- function(resolution,lon,lat) {
  v_lat = 37.6895
  v_lon = -51.6218
  azimuth = 360-72.6482
  DGG = dgconstruct(projection = "ISEA", aperture = 3, topology = "HEXAGON", res = resolution, 
                       precision = 7, azimuth_deg =  azimuth, pole_lat_deg = v_lat, pole_lon_deg = v_lon)
  Cell_address = dgGEO_to_SEQNUM(DGG,lon,lat)$seqnum
  lon_c = dgSEQNUM_to_GEO(DGG,Cell_address)$lon_deg
  lat_c = dgSEQNUM_to_GEO(DGG,Cell_address)$lat_deg
  lon_lat = c(lon_c,lat_c)
  return (lon_lat)
}
''')

def fall_in(x,y):
    ''' check if the point falls in HRDEM extent '''
    point = shapely.geometry.Point(x,y)
    if point.within(HRDEM_extent):
        return 1
    else:
        return 0

def catch(func, dem, handle = lambda e : e, *args, **kwargs):
    ''' Handle the try except in a general function'''
    try:
        return func(*args, **kwargs)
    except:
        if dem == 'CDEM':
            return -32767
        elif dem == 'HRDEM':
            return numpy.nan

def pre_dggs_elevation(dataframe):
    ''' A function on the dataframe to resample DEM by nearest neighbor method '''
    coords = [(lon,lat) for lon, lat in zip(dataframe.lon, dataframe.lat)]
    dataframe['CDEM'] = [catch(lambda: elev[0],'CDEM') for elev in CDEM_TIF.sample(coords)]
    dataframe['HRDEM'] = [catch(lambda: elev[0],'HRDEM') for elev in HRDEM_TIF.sample(coords)]
    return dataframe

# define a function to find neighbors for interpolation
def find_neighbor(x,y,dataset):
    ''' 
    Find neighbors for interpolation --
    determine the DEM source
    find out the 9 neighbors geographic coords
    extract the elevations at these 9 coords
    convert 9 coords to array index then back to 9 coords of grid mesh centers
    '''
    if dataset == 'HRDEM':
        pixelSizeX, pixelSizeY = HRDEM_pixelSizeX,HRDEM_pixelSizeY
        DEM_TIF= HRDEM_TIF
    elif dataset == 'CDEM':
        pixelSizeX, pixelSizeY = CDEM_pixelSizeX,CDEM_pixelSizeY
        DEM_TIF = CDEM_TIF  
    x_coord,y_coord = [x-pixelSizeX,x,x+pixelSizeX],[y-pixelSizeY,y,y+pixelSizeY]
    x_coord,y_coord = numpy.repeat(x_coord,3),numpy.array(y_coord*3)
    coords = [(lon,lat) for lon, lat in zip(x_coord,y_coord)]
    z_array = [elev[0] for elev in DEM_TIF.sample(coords)]
    x_index,y_index = rasterio.transform.rowcol(DEM_TIF.transform, x_coord, y_coord)
    x_array,y_array = rasterio.transform.xy(DEM_TIF.transform, x_index, y_index)
    return x_array, y_array, z_array

# define an extract-from-raster function to get post DGGS-modeled value
# still need to check if cell centroid falls in the HRDEM extent instead of using the field fall_in_test
# because a original control point falls in does not necessarily mean the corresponding cell centroid falls in

def dggs_elevation_cdem(lon,lat,resolution,interp = 'linear'):
    ''' 
    Resample CDEM -- 
    if an error is raised then return -32767 as its final elevation
    if the point or any of its neighbors has the value -32767 then return -32767 as its final elevation
    if none of its neighbor has value -32767 then interpolate elevation
    restrict the decimal places according to the look-up table defined earlier 
    '''
    dataset = 'CDEM'
    x_y = conn.eval('geo_to_centroid('+str(resolution)+','+str(lon)+','+str(lat)+')')
    x,y = x_y[0],x_y[1]
    try:
        x_array, y_array, z_array = find_neighbor(x,y,dataset)
        if -32767 in z_array:
            return -32767
        else:
            CDEM_interp = interpolate.interp2d(x_array, y_array, z_array, kind=interp)
            elevation = CDEM_interp(x,y)[0]
            vertical_res = look_up.loc[resolution,'verti_res']
            elevation = round(elevation,vertical_res)
            return elevation
    except:
        return -32767

def dggs_elevation_hrdem(lon,lat,resolution,interp = 'linear'):
    ''' 
    Resample HRDEM -- 
    if the point falls in the HRDEM data extend then proceed
    if the point or any of its neighbors has the value -32767 then pass
    if an error is raised then pass
    restrict the decimal places according to the look-up table defined earlier 
    '''
    dataset = 'HRDEM'
    x_y = conn.eval('geo_to_centroid('+str(resolution)+','+str(lon)+','+str(lat)+')')
    x,y = x_y[0],x_y[1]
    point = shapely.geometry.Point(x,y)
    if point.within(HRDEM_extent):
        try:
            x_array, y_array, z_array = find_neighbor(x,y,dataset)
            if -32767 in z_array:
                return numpy.nan
            else:
                HRDEM_interp = interpolate.interp2d(x_array, y_array, z_array, kind=interp)
                elevation = HRDEM_interp(x,y)[0]
                vertical_res = look_up.loc[resolution,'verti_res']
                elevation = round(elevation,vertical_res)
                return elevation
        except:
            return numpy.nan
    else:
        return numpy.nan

# read control points dataset
control_points = pandas.read_csv('Experiment_data/vege_checked.csv', sep=',')

# test if the control point falls in HRDEM extent and store in a field
control_points['fall_in_test'] = [fall_in(lon,lat) for lon, lat in zip(control_points.lon, control_points.lat)]

# calculate the pre-DGGS elevation
control_points = pre_dggs_elevation(control_points)
control_points['pre_DGGS_Elev'] = numpy.where(numpy.isnan(control_points['HRDEM']), control_points['CDEM'], control_points['HRDEM'])

# calculate the post-DGGS elevation
# apply the dggs_elevation fuction for each control point at each level
for i in range(16,30):
    control_points['model_CDEM_{}'.format(i)] = control_points.apply(lambda row: dggs_elevation_cdem(row['lon'],row['lat'],i), axis=1)
    control_points['model_HRDEM_{}'.format(i)] = control_points.apply(lambda row: dggs_elevation_hrdem(row['lon'],row['lat'],i), axis=1)
    control_points['model_Elev_{}'.format(i)] = numpy.where(numpy.isnan(control_points['model_HRDEM_{}'.format(i)]), control_points['model_CDEM_{}'.format(i)], control_points['model_HRDEM_{}'.format(i)])

# save to csv
control_points.to_csv("Result/gcp_result.csv", index=False)

conn.shutdown()
print("Processing time: %s seconds" % (time.time() - start_time))
