###########################################################
#### DGGS modeling -- extract values with interpolation ###
###########################################################

import sys, os
import rasterio, geopandas, shapely
import pandas, numpy
import multiprocess as mp
from scipy import interpolate
import warnings
import time

shapely.speedups.enable()
warnings.simplefilter('error', RuntimeWarning) 

## set script argument -- resolution level and grid number
dggs_res = int(sys.argv[1])
fid = int(os.environ.get("SLURM_ARRAY_TASK_ID"))

## construct a look-up table, storing resolution and corresponding cell size and vertical resolution
res_list = [16,17,18,19,20,21,22,23,24,25,26,27,28,29]
cell_size_list = [0.005,0.003,0.001,0.0009,0.0008,0.0006,0.0003,0.0002,0.0001,0.00006,0.00003,0.00002,0.00001,0.000005]
vertical_res_list = [0,0,0,1,1,2,2,3,3,4,4,5,5,6]
# convert to a pandas dataframe with resolution levels as index
look_up = pandas.DataFrame({'res': res_list, 'cell_size': cell_size_list, 'verti_res': vertical_res_list}, index = res_list)

# look up cellsize and vertical resolution
dggs_cellsize = look_up.loc[dggs_res,'cell_size']
vertical_res = look_up.loc[dggs_res,'verti_res']

## read the csv into a dataframe
input_csv_path = 'Result/Level{}/Centroid/vege_pre_{}.csv'.format(dggs_res,fid)
fishnet_df = pandas.read_csv(input_csv_path, sep=',', usecols=['Cell_address', 'lon_c', 'lat_c'])

## Prepare HRDEM_extent polygons
HRDEM_extent = geopandas.GeoDataFrame.from_file('Data/Projects_Footprints_dissolved.shp')
HRDEM_extent = HRDEM_extent.to_crs("EPSG:4617") # NAD83 CSRS

## Read DEMs -- CDEM + HRDEM
CDEM_TIF = rasterio.open('Data/CDEM_cgvd2013.tif')
HRDEM_TIF = rasterio.open('Data/HRDEM_cgvd2013.tif')

## Define the main funcitons    
def find_neighbor(x,y,DEM_TIF):
    ''' 
    Find neighbors for interpolation --
    determine the DEM source
    find out the 4 neighbors geographic coords
    extract the elevations at these 4 coords
    convert 4 coords to array index then back to 4 coords of grid mesh centers
    '''
    x_index,y_index = rasterio.transform.rowcol(DEM_TIF.transform, x,y)
    xc,yc = rasterio.transform.xy(DEM_TIF.transform, x_index, y_index)
    if x > xc and y > yc:
        x_index_array = [x_index-1,x_index-1,x_index,x_index]
        y_index_array = [y_index,y_index+1,y_index,y_index+1]
    elif x > xc and y < yc:
        x_index_array = [x_index,x_index,x_index+1,x_index+1]
        y_index_array = [y_index,y_index+1,y_index,y_index+1]
    elif x < xc and y > yc:
        x_index_array = [x_index-1,x_index-1,x_index,x_index]
        y_index_array = [y_index-1,y_index,y_index-1,y_index]
    elif x < xc and y < yc:
        x_index_array = [x_index,x_index,x_index+1,x_index+1]
        y_index_array = [y_index-1,y_index,y_index-1,y_index]
    x_array,y_array = rasterio.transform.xy(DEM_TIF.transform, x_index_array, y_index_array)
    coords = [(lon,lat) for lon, lat in zip(x_array,y_array)]
    z_array = [elev[0] for elev in DEM_TIF.sample(coords)]
    return x_array, y_array, z_array

def dggs_elevation_cdem(x,y,interp = 'linear'):
    ''' 
    Resample CDEM -- 
    if an error is raised then return -32767 as its final elevation
    if the point or any of its neighbors has the value -32767 then return -32767 as its final elevation
    if none of its neighbor has value -32767 then interpolate elevation
    restrict the decimal places according to the look-up table defined earlier 
    '''
    DEM_TIF = CDEM_TIF
    try:
        x_array, y_array, z_array = find_neighbor(x,y,DEM_TIF)
        if -32767 in z_array:
            return -32767
        else:
            CDEM_interp = interpolate.interp2d(x_array, y_array, z_array, kind=interp)
            elevation = CDEM_interp(x,y)[0]
            elevation = round(elevation,vertical_res)
            return elevation
    except:
        return -32767

def dggs_elevation_hrdem(x,y,interp = 'linear'):
    ''' 
    Resample HRDEM -- 
    if the point falls in the HRDEM data extend then proceed
    if the point or any of its neighbors has the value -32767 then pass
    if an error is raised then pass
    restrict the decimal places according to the look-up table defined earlier 
    '''
    DEM_TIF = HRDEM_TIF
    point = shapely.geometry.Point(x,y)
    if point.within(HRDEM_extent.geometry[0]):
        try:
            x_array, y_array, z_array = find_neighbor(x,y,DEM_TIF)
            if -32767 in z_array:
                pass
            else:
                HRDEM_interp = interpolate.interp2d(x_array, y_array, z_array, kind=interp)
                elevation = HRDEM_interp(x,y)[0]
                elevation = round(elevation,vertical_res)
                return elevation
        except:
            pass
    else:
        pass
    
def dggs_elevation_df(dataframe):
    ''' a function on the dataframe so that it can be called on splitted data chunks'''
    dataframe['model_cdem'] = [dggs_elevation_cdem(lon,lat) for lon, lat in zip(dataframe.lon_c, dataframe.lat_c)]
    dataframe['model_hrdem'] = [dggs_elevation_hrdem(lon,lat) for lon, lat in zip(dataframe.lon_c, dataframe.lat_c)]
    return dataframe

# record timing -- start
start_time = time.time()

# call the function by parallel processing
n_cores = int(os.environ.get('SLURM_CPUS_PER_TASK',default=1))
fishnet_df_split = numpy.array_split(fishnet_df, n_cores)
pool = mp.Pool(processes = n_cores)
fishnet_df_output = pandas.concat(pool.map(dggs_elevation_df, fishnet_df_split))
pool.close()
pool.join()

# record timing -- end
print (dggs_res)
print ("Processing time: %s seconds" % (time.time() - start_time))

# save the results as csv
output_csv_path = 'Result/Level{}/Elev/vege_elev_{}.csv'.format(dggs_res,fid)
fishnet_df_output = fishnet_df_output.drop(columns=['lon_c','lat_c'])
fishnet_df_output.to_csv(output_csv_path, index=False)
