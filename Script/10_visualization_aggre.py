import datashader as ds, matplotlib.pyplot as plt, pandas as pd
import sys, gc, matplotlib
from datashader.mpl_ext import dsshow

matplotlib.use('AGG')
dggs_res = int((sys.argv[1]))
grid_num = int((sys.argv[2]))

for fid in range(1,grid_num+1):
    centroid_df = pd.read_csv('Result/Level{}/Centroid/vege_pre_{}.csv'.format(dggs_res,fid))
    elev_df = pd.read_csv('Result/Level{}/Stats/vege_temp_{}.csv'.format(dggs_res,fid))
    
    merge_df = pd.merge(left = elev_df, right = centroid_df, how="inner", on="Cell_address")
    del centroid_df,elev_df
    gc.collect()
    
    # mean
    fig, ax = plt.subplots()
    artist = dsshow(merge_df, ds.Point('lon_c', 'lat_c'), aggregator = ds.mean('elev_mean'), cmap = 'gray', vmin = 0, vmax = 600, plot_width=500, plot_height=500, ax = ax)
    
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis("off")
    
    plt.savefig('Result/Level{}/Img/vege_mean_{}.png'.format(dggs_res,fid), bbox_inches='tight', pad_inches=0.0)
    plt.close()
    gc.collect()
    
    # max
    fig, ax = plt.subplots()
    artist = dsshow(merge_df, ds.Point('lon_c', 'lat_c'), aggregator = ds.max('elev_max'), cmap = 'gray', vmin = 0, vmax = 600, plot_width=500, plot_height=500, ax = ax)
    
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis("off")
    
    plt.savefig('Result/Level{}/Img/vege_max_{}.png'.format(dggs_res,fid), bbox_inches='tight', pad_inches=0.0)
    plt.close()
    gc.collect()
    
    # min
    fig, ax = plt.subplots()
    artist = dsshow(merge_df, ds.Point('lon_c', 'lat_c'), aggregator = ds.min('elev_min'), cmap = 'gray', vmin = 0, vmax = 600, plot_width=500, plot_height=500, ax = ax)
    
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis("off")
    
    plt.savefig('Result/Level{}/Img/vege_min_{}.png'.format(dggs_res,fid), bbox_inches='tight', pad_inches=0.0)
    plt.close()
    gc.collect()
        