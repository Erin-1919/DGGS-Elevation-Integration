###################################################
#### HRDEM pre-processing (reproject + mosaic)  ###
###################################################

### inversely project HRDEM to geographic CRS
import glob, rasterio, gdal

def reverse_projection(input_dem,output_dem):
    ''' A function to reversely project HRDEM (m) to the geographic space (degree) '''
    hrdem = rasterio.open(input_dem)
    wrap_option = gdal.WarpOptions(format = hrdem.meta.get('driver'), 
                       outputType = gdal.GDT_Float32,
                       srcSRS = hrdem.meta.get('crs'),
                       dstSRS = 'EPSG:4617', # NAD83(CSRS)
                       dstNodata = hrdem.meta.get('nodata'),
                       creationOptions = ['COMPRESS=LZW'])
    gdal.Warp(output_dem, input_dem, options = wrap_option)

# find out all HRDEM datasets in the Data directory
HRDEM_TIFS = glob.glob('Data/HRDEM_*.tif')

for tif in HRDEM_TIFS:  
    out = tif[:-4]+'_4617.tif' # be careful index is hardcoded!
    reverse_projection(tif,out)

print ("Inversely project HRDEM successfully!")

### mosaic HRDEMs
import gc
from rasterio.merge import merge

dem_fps = glob.glob('Data/HRDEM_*_4617.tif')
src_files_to_mosaic = []

for fp in dem_fps:
    src = rasterio.open(fp)
    src_files_to_mosaic.append(src)
    
# Merge function returns a single mosaic array and the transformation info
mosaic_dem, mosaic_trans = merge(src_files_to_mosaic, res=src.res, nodata=-32767.0, method='first')

# Copy the metadata
mosaic_meta = src.meta.copy()

# Update the metadata
mosaic_meta.update({"driver": "GTiff","height": mosaic_dem.shape[1],"width": mosaic_dem.shape[2], "compress":'lzw', 
                    "count":1,"dtype": 'float32',"nodata": -32767.0,"transform": mosaic_trans,"crs": "EPSG:4617"})

# Write the mosaic raster to disk
with rasterio.open("Data/HRDEM_mosaic.tif", "w", **mosaic_meta) as dest:
    dest.write(mosaic_dem)

src.close()
del mosaic_dem, mosaic_trans, mosaic_meta
gc.collect()

print ("Mosaic HRDEMs successfully!")