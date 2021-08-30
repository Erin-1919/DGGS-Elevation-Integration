###########################################################
#### Elevation generalization -- multiple stats on elev ###
###########################################################

import numpy, sys, pandas, gc, os
import multiprocess as mp
import time

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

## read the csv into a dataframe and join tables based on cell index at fine level
if dggs_res == 28:
    elev_csv_path = "Result/Level{}/Elev/vege_temp_{}.csv".format(dggs_res+1,fid)
else:
    elev_csv_path = "Result/Level{}/Stats/vege_temp_{}.csv".format(dggs_res+1,fid)
cell_csv_path = "Result/Level{}/Temp/vege_temp_{}.csv".format(dggs_res,fid)
cell_df = pandas.read_csv(cell_csv_path, sep=',',index_col = 'cell_fine')
elev_df = pandas.read_csv(elev_csv_path, sep=',',index_col = 'Cell_address')
join_df = cell_df.join(elev_df,how = 'left')
del cell_df, elev_df
gc.collect()

def elev_stats(dataframe):
    ''' do stats on elev '''
    if dggs_res == 28:
        dataframe['elev_stats'] = numpy.where(numpy.isnan(dataframe['model_hrdem']), dataframe['model_cdem'], dataframe['model_hrdem'])
        dataframe = dataframe.drop(columns=['model_hrdem','model_cdem'])
        join_stats_df = dataframe.groupby(["cell"]).agg(elev_mean = ('elev_stats',numpy.mean), elev_max = ('elev_stats',numpy.max), elev_min = ('elev_stats',numpy.min))
    else:
        join_stats_df = dataframe.groupby(["cell"]).agg(elev_mean = ('elev_mean',numpy.mean), elev_max = ('elev_max',numpy.max), elev_min = ('elev_min',numpy.min))
    join_stats_df['elev_mean'] = [round(row,vertical_res) for row in join_stats_df['elev_mean']]
    join_stats_df['elev_max'] = [round(row,vertical_res) for row in join_stats_df['elev_max']]
    join_stats_df['elev_min'] = [round(row,vertical_res) for row in join_stats_df['elev_min']]
    join_stats_df.index.names = ['Cell_address']
    return join_stats_df

def genDf(n):
    return vc[vc.bin == n].index

# record timing -- start
start_time = time.time()

# call the function by parallel processing
n_cores = int(os.environ.get('SLURM_CPUS_PER_TASK',default=1))
vc = join_df.cell.value_counts().rename('cnt')
vc = vc.to_frame().assign(bin=[ i % n_cores for i in range(vc.size)])
df_split = [ join_df[join_df.cell.isin(genDf(i))] for i in range(n_cores) ]
pool = mp.Pool(processes = n_cores)
df_output = pandas.concat(pool.map(elev_stats, df_split))
pool.close()
pool.join()

# record timing -- end
print ("Processing time: %s seconds" % (time.time() - start_time))

# save the csv
output_csv_path = "Result/Level{}/Stats/vege_temp_{}.csv".format(dggs_res,fid)
