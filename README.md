# DGGS-Elevation-Integration

This work aimed to integrate multi-source terrain data in Canada by adopting the ISEA3H DGGS. The modeling process of terrain data in the ISEA3H DGGS had the following main phases: data acquisition, pre-processing, quantization, aggregation, and quality control. The open-sourced library [*dggridR*](https://github.com/r-barnes/dggridR) was used to complete conversion between geographic locations and ISEA3H DGGS cell indices. The modeling process was developed using a hybrid of Python and R environments.

The following libraries are needed:

*Python*
 - geopandas
 - shapely
 - numpy
 - math
 - requests
 - zipfile
 - json
 - gc
 - glob
 - rasterio
 - gdal
 - pandas
 - multiprocess
 - scipy
 - warnings
 - time
 - pyRserve
 - datashader
 - matplotlib

*R*
 - dggridR
 - rgdal
 - rgeos
 - dplyr
 - doParallel
 - tictoc

Sample job scripts sent to high-performance cluster are provided in the folder [*Sample_job_script*](https://github.com/Erin-1919/DGGS-Elevation-Integration/tree/main/Sample_job_script).
