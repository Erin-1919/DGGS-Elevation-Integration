##################################################
########### Parent-child look-up tables ##########
##################################################

library(dggridR)
library(dplyr)
library(doParallel)
library(tictoc)

# read arguments, resolution level and grid ID
sys.argv = commandArgs(trailingOnly = TRUE)
dggs_res = as.numeric((sys.argv[1]))
fid = as.numeric(Sys.getenv("SLURM_ARRAY_TASK_ID"))

# read csv files
coarse.df = read.csv(sprintf("Result/Level%d/Centroid/vege_pre_%d.csv",dggs_res,fid),header = TRUE)[,c("Cell_address","lon_c","lat_c")]

# define elev stats function
elev_stats = function(resolution,dataframe) {
  v_lat = 37.6895
  v_lon = -51.6218
  azimuth = 360-72.6482
  # construct two dggs on two levels
  dgg.coarse = dgconstruct(projection = "ISEA", aperture = 3, topology = "HEXAGON", res = resolution, 
                    precision = 7, azimuth_deg =  azimuth, pole_lat_deg = v_lat, pole_lon_deg = v_lon)
  dgg.fine = dgconstruct(projection = "ISEA", aperture = 3, topology = "HEXAGON", res = (resolution+1), 
                    precision = 7, azimuth_deg =  azimuth, pole_lat_deg = v_lat, pole_lon_deg = v_lon)
  vertices.df = dgcellstogrid(dgg.coarse,dataframe$Cell_address)
  vertices.df = filter(vertices.df, order < 7)
  vertices.df = subset(vertices.df, select = -c(order,hole,piece,group))
  vertices.df = vertices.df[,c("cell","long","lat")]
  dataframe = dataframe %>% rename(cell = Cell_address,long = lon_c,lat = lat_c)
  vertices.df = rbind(vertices.df,dataframe)
  vertices.df$cell_fine = dgGEO_to_SEQNUM(dgg.fine,vertices.df$long,vertices.df$lat)$seqnum
  vertices.df = subset(vertices.df, select = -c(long,lat))
  return (vertices.df)
}

# get number of cores, register at the backend, and split the dataframe into N (=cores) chunks
ncores = Sys.getenv("SLURM_CPUS_PER_TASK") 
registerDoParallel(cores=ncores)# Shows the number of Parallel Workers to be used
coarse.df.split = split(coarse.df,sample(1:ncores, nrow(coarse.df), replace=T))
rm (coarse.df)

print (dggs_res)
tic("generate temps: ")

# be careful! foreach() and %dopar% must be on the same line!
output_df = foreach(df = coarse.df.split, .combine=rbind,.packages='dggridR') %dopar% {elev_stats(dggs_res,df)}
toc()

# save results
write.csv(output_df,sprintf("Result/Level%d/Temp/vege_temp_%d.csv",dggs_res,fid),row.names = FALSE)

