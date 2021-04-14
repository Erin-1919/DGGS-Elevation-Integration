###################################################
################## download data ##################
###################################################

### set script argument -- bounding box coords of the area of interest
import sys

minx = float((sys.argv[1]))
miny = float((sys.argv[2]))
maxx = float((sys.argv[3]))
maxy = float((sys.argv[4]))
grid_num = int((sys.argv[4]))
crs = (sys.argv[5])

# minx = -80.4227847532
# miny = 43.3203845275
# maxx = -78.9227847532
# maxy = 44.8203845275
# grid_num = 100
# crs = 'utm17'

### create shp for the bbox
import geopandas as gpd
from shapely.geometry import Polygon

# lat lon coords of bbox in two lists
lat_point_list = [maxy,maxy,miny,miny,maxy]
lon_point_list = [minx,maxx,maxx,minx,minx]

# create shapely polygon
polygon_geom = Polygon(zip(lon_point_list, lat_point_list))
polygon = gpd.GeoDataFrame(index=[0], crs={'init': 'epsg:4617'}, geometry=[polygon_geom])       
print(polygon.geometry)

# output polygon as an Esri shapefile
polygon.to_file(filename='Data/study_area.shp', driver="ESRI Shapefile")

print ("Study area shp is created successfully!")

### create fishnet grid for future usage
import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon
from math import sqrt

length = (maxx-minx)/sqrt(grid_num)
wide = (maxy-miny)/sqrt(grid_num)

cols = list(np.arange(minx, maxx + wide, wide))
rows = list(np.arange(miny, maxy + length, length))

polygons = []
for x in cols[:-1]:
    for y in rows[:-1]:
        polygons.append(Polygon([(x,y), (x+wide, y), (x+wide, y+length), (x, y+length)]))

grid = gpd.GeoDataFrame({'geometry':polygons})
grid.to_file('fishnet_grid.shp')

print ("Fishnet grid shp is created successfully!")

### download data
import requests, zipfile, json
import geopandas as gpd

## download dataset footprint shapefile
url_df = 'https://ftp.maps.canada.ca/pub/elevation/dem_mne/highresolution_hauteresolution/Datasets_Footprints.zip'
r_df = requests.get(url_df, allow_redirects=True)
zip_df = 'Data/Datasets_Footprints.zip'
open(zip_df, 'wb').write(r_df.content)

# unzip
with zipfile.ZipFile(zip_df,"r") as zip_ref:
    zip_ref.extractall("Data")

print ("Datasets Footprints are downloaded successfully!")

## download project footprint shapefile
url_pf = 'https://ftp.maps.canada.ca/pub/elevation/dem_mne/highresolution_hauteresolution/Projects_Footprints.zip'
r_pf = requests.get(url_pf, allow_redirects=True)
zip_pf = 'Data/Projects_Footprints.zip'
open(zip_pf, 'wb').write(r_pf.content)

# unzip
with zipfile.ZipFile(zip_pf,"r") as zip_ref:
    zip_ref.extractall("Data")

print ("Projects Footprints are downloaded successfully!")

## clean up the project footprint shp a bit
# read data
Projects_Footprints = gpd.GeoDataFrame.from_file('Data/Projects_Footprints.shp')
Study_Area = gpd.GeoDataFrame.from_file('Data/study_area.shp')

# clip the project footprint to the extent of study area
Projects_Footprints_clipped = gpd.clip(Projects_Footprints, Study_Area)

# dissolve all polygons 
Projects_Footprints_clipped['dissolvefield'] = 1
Projects_Footprints_clipped = Projects_Footprints_clipped[['dissolvefield', 'geometry']]
Projects_Footprints_dissolved = Projects_Footprints_clipped.dissolve(by='dissolvefield')

# output polygon as an Esri shapefile
Projects_Footprints_dissolved.to_file(filename='Data/Projects_Footprints_dissolved.shp', driver="ESRI Shapefile")

print ("Projects Footprints are prepared!")

## download CDEM
# STAC API search endpoint
stac_cdem = "https://datacube.services.geo.ca/api/search?collections=cdem&bbox={},{},{},{}".format(minx,miny,maxx,maxy)

# POST request adding the defined payload
response_cdem = requests.request("GET", stac_cdem)

# Load response as JSON
json_object = json.loads(response_cdem.text)
print(json.dumps(json_object, indent=2))

# create empty lists to store url and file names
url_cdem_list=[]
file_cdem_list = []

# loop through the coverages returned
for f in json_object['features']:
    url_cdem_list.append(f['assets']['dem']['href'])

# fill the file name list
for i in range(1,len(url_cdem_list)+1):
    file_cdem_list.append('Data/CDEM_'+ str(i) + '.tif')

# loop through the url list and download each tiff
for url, tif in zip(url_cdem_list, file_cdem_list):
    r = requests.get(url, allow_redirects=True)
    open(tif, 'wb').write(r.content)
    print ("Download "+tif)

print ("CDEM are downloaded successfully!")

## download HRDEM
# read data
Datasets_Footprints = gpd.GeoDataFrame.from_file('Data/Datasets_Footprints.shp')
#Study_Area = gpd.GeoDataFrame.from_file('Data/study_area.shp')

# filter out the intersected tiles
join = gpd.sjoin(Datasets_Footprints, Study_Area, how="inner", op="intersects")
join = join[['Coord_Sys','Ftp_dtm']]
join = join[join['Coord_Sys'] == crs]

# store url and file names in lists
url_hrdem_list = join['Ftp_dtm'].tolist()
file_hrdem_list = []

# fill the file name list
for i in range(1,len(url_hrdem_list)+1):
    file_hrdem_list.append('Data/HRDEM_'+ str(i) + '.tif')

# loop through the url list and download each tiff
for url, tif in zip(url_hrdem_list, file_hrdem_list):
    r = requests.get(url, allow_redirects=True)
    open(tif, 'wb').write(r.content)
    print ("Download "+tif)

print ("HRDEM are downloaded successfully!")