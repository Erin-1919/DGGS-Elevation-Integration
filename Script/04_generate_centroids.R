library(dggridR)
library(rgdal)
library(rgeos)
library(dplyr)
library(doParallel)
library(tictoc)

# read arguments, resolution level and grid ID
sys.argv = commandArgs(trailingOnly = TRUE)
dggs_res = as.numeric((sys.argv[1]))
fid = as.numeric(Sys.getenv("SLURM_ARRAY_TASK_ID"))

# get number of cores, register at the backend
ncores = as.numeric(Sys.getenv("SLURM_CPUS_PER_TASK")) 
registerDoParallel(cores=ncores)# Shows the number of Parallel Workers to be used

# construct a look-up table, storing resolution and corresponding cell size and vertical resolution
res_list = c(16,17,18,19,20,21,22,23,24,25,26,27,28,29)
cell_size_list = c(0.005,0.005,0.003,0.001,0.001,0.0006,0.0003,0.0002,0.0001,0.00007,0.00003,0.00002,0.00001,0.000005)
vertical_res_list = c(0,0,0,1,1,2,2,3,3,4,4,5,5,6)
look_up = data.frame("res_list" = res_list,"cell_size_list" = cell_size_list,"vertical_res_list" = vertical_res_list)

# look up cell size and vertical resolution
dggs_cellsize = look_up$cell_size_list[look_up$res_list == dggs_res]
vertical_res = look_up$vertical_res_list[look_up$res_list == dggs_res]

# define DGGS
v_lat = 37.6895
v_lon = -51.6218
azimuth = 360-72.6482
DGG = dgconstruct(projection="ISEA", aperture=3, topology="HEXAGON", res=dggs_res, azimuth_deg=azimuth, pole_lat_deg=v_lat, pole_lon_deg=v_lon)

# define a function to generate nested grids
nested_grids = function(sqnum) {
  fishnet_all = readOGR(dsn="Data",layer='fishnet_grid')
  fishnet = bbox(fishnet_all[fid,])
  minx = fishnet[1,1]
  miny = fishnet[2,1]
  maxx = fishnet[1,2]
  maxy = fishnet[2,2]
  width = max((maxx-minx),(maxy-miny))/(2*sqrt(sqnum))
  coords = matrix(c(minx, miny, maxx, miny, maxx, maxy, maxx, miny, minx, miny), byrow = TRUE, ncol = 2)
  regbox = Polygon(coords)
  regbox = SpatialPolygons(list(Polygons(list(regbox), ID = "a")), proj4string=CRS("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"))
  reg_points = sp::makegrid(regbox, n = sqnum)
  reg_points = sp::SpatialPoints(cbind(reg_points$x1,reg_points$x2))
  reg_grid = rgeos::gBuffer(reg_points,byid = TRUE, width=width, capStyle = "SQUARE")
  return (reg_grid)
}

# define a function to find cell centroids position within a rectangle searching area
find_centroid = function(i,cellsize) {
  centroids = sp::makegrid(rectangles[i], cellsize = cellsize)
  centroids$Cell_address = dgGEO_to_SEQNUM(DGG,centroids$x1, centroids$x2)$seqnum
  centroids = centroids[!duplicated(centroids$Cell_address),]
  centroids$lon_c = dgSEQNUM_to_GEO(DGG,centroids$Cell_address)$lon_deg
  centroids$lat_c = dgSEQNUM_to_GEO(DGG,centroids$Cell_address)$lat_deg
  centroids = subset(centroids, select = -c(x1,x2) )
  return (centroids)
}

# call function nested_grids
rectangles = nested_grids(ncores)

# record timing -- start
tic()

# conduct parallel processing
output_df = foreach(i=c(1:ncores), .combine=rbind,.packages='dggridR') %dopar% {find_centroid(i,dggs_cellsize)}
output_df = output_df[!duplicated(output_df$Cell_address),]

# record timing -- end
print (dggs_res)
toc()

# save results
write.csv(output_df,sprintf("Result/Level%d/Centroid/vege_pre_%d.csv",dggs_res,fid),row.names = FALSE)
