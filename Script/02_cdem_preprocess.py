###################################################
#### CDEM pre-processing (convert to CGVD2013)  ###
###################################################

### mosaic CDEMs
import gc, glob, rasterio, os
from rasterio.merge import merge

# find out all CDEMs in the folder
dem_fps = glob.glob('Data/CDEM_*.tif')
src_files_to_mosaic = []

for fp in dem_fps:
    src = rasterio.open(fp)
    src_files_to_mosaic.append(src)

if len(src_files_to_mosaic) == 1:
    src.close()
    os.rename('Data/CDEM_1.tif', 'Data/CDEM_mosaic.tif')
else:
    # Merge function returns a single mosaic array and the transformation info
    mosaic_dem, mosaic_trans = merge(src_files_to_mosaic, res=src.res, nodata=-32767.0, method='first')
    # Copy the metadata
    mosaic_meta = src.meta.copy()
    # Update the metadata
    mosaic_meta.update({"driver":"GTiff","height":mosaic_dem.shape[1],"width":mosaic_dem.shape[2], "compress":'lzw', 
                        "count":1,"nodata":-32767.0,"transform":mosaic_trans,"crs":"EPSG:4617"})
    # Write the mosaic raster to disk
    with rasterio.open("Data/CDEM_mosaic.tif", "w", **mosaic_meta) as dest:
        dest.write(mosaic_dem)
    src.close()
    del mosaic_dem, mosaic_trans, mosaic_meta
    gc.collect()

print ("Mosaic CDEMs successfully!")

### inversely project CDEM to geographic CRS
import rasterio, gdal

cdem_mosaic = rasterio.open('Data/CDEM_mosaic.tif')

wrap_option = gdal.WarpOptions(format = cdem_mosaic.meta.get('driver'), 
                   outputType = gdal.GDT_Float32,
                   srcSRS = cdem_mosaic.meta.get('crs'),
                   dstSRS = 'EPSG:4617', # NAD83(CSRS)
                   dstNodata = cdem_mosaic.meta.get('nodata'),
                   creationOptions = ['COMPRESS=LZW'])

gdal.Warp('Data/CDEM_mosaic_4617.tif', 'Data/CDEM_mosaic.tif', options = wrap_option)

print ("Inversely project CDEM successfully!")
    
### convert to CGVD2013 
import json, rasterio, numpy
import geopandas as gpd
from rasterio.mask import mask

# load rasters
cdem_cgvd1928 = rasterio.open('Data/CDEM_mosaic_4617.tif')
byn = rasterio.open('Data/HT2_2010v70_CGG2013a.byn')

# load study area shp
boundingbox_gdf = gpd.GeoDataFrame.from_file('Data/study_area.shp')
boundingbox_gdf = boundingbox_gdf.set_crs("EPSG:4617") # NAD83 CSRS

def getFeatures(gdf):
    ''' A funcion to parse features from GeoDataFrame in such a manner that rasterio wants them '''
    return [json.loads(gdf.to_json())['features'][0]['geometry']]

# call the function to get coords in json
boundingbox_coords = getFeatures(boundingbox_gdf)

# crop the mosaic CDEM to the extent of study area
cdem_out_img, cdem_out_transform = mask(dataset=cdem_cgvd1928, shapes=boundingbox_coords, crop=True)
cdem_out_meta = cdem_cgvd1928.meta.copy()
cdem_out_meta.update({"dtype": 'float32', "compress":'lzw'})

cdem_cgvd1928.close()

# crop the byn to the extent of the study area
byn_out_img, byn_out_transform = mask(dataset=byn, shapes=boundingbox_coords, crop=True)
byn_out_meta = cdem_cgvd1928.meta.copy()
byn_out_meta.update({"dtype": 'int32', "compress":'lzw'})

byn.close()

# output clipped rasters
with rasterio.open('Data/CDEM_mosaic_clip.tif', "w", **cdem_out_meta) as dest:
    dest.write(cdem_out_img)

with rasterio.open('Data/byn_clip.tif', "w", **byn_out_meta) as dest:
    dest.write(byn_out_img)

del cdem_out_img, cdem_out_transform, byn_out_img, byn_out_transform
gc.collect()

clipped_cdem = rasterio.open('Data/CDEM_mosaic_clip.tif')
clipped_byn = rasterio.open('Data/byn_clip.tif')

# do map algebra
delta_dem = clipped_byn.read(1)
cgvd1928 = clipped_cdem.read(1)
cgvd2013 = cgvd1928 - delta_dem/1000
cgvd2013 = numpy.where(cgvd2013 < -32000, -32767, cgvd2013)

# update the output tif metadata
cgvd2013_meta = clipped_cdem.meta.copy()
cgvd2013_meta.update({"dtype": 'float64', "compress":'lzw'})

# output the tif with cgvd2013 values
with rasterio.open('Data/CDEM_cgvd2013.tif', "w", **cgvd2013_meta) as dest:
    dest.write(cgvd2013.astype(rasterio.float64), 1)

print ("Convert to CGVD2013 successfully!")

