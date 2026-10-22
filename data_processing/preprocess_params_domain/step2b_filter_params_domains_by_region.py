#Abigail Birnbaum (abigail.birnbaum@pnnl.gov)
#Last updated: 2026-10-01
#Script to filter params.nc and domain.nc files (originally for all of North America) by HUC-2/PFAF region. 
#Adds in a buffer of 1/16 degrees of the bounds of the shapefiles

#Import statements
import numpy as np
import pandas as pd
import xarray as xr
import time

start_time = time.time()

#specify paths to data
pwp = '/gcfs/projects/foresight/hydrology/'
dir_path = pwp+'abirn_vic/input_data/'
region_bounds_path = dir_path+'extra_spatial_data/region_bounds.csv' #path to region boundaries csv file
na_domain_path = dir_path+'initial_input_data/namerica_domain.nc' #path to VIC-global domain file
na_params_path = dir_path+'initial_input_data/namerica_params.nc' #path to VIC-global params file
save_params_path = dir_path+'params_by_huc2/' #path to save params by huc-2 or pfaf region
save_domain_path = dir_path+'domain_by_huc2/' #path to save domain by huc-2 or pfaf region

#read in domain and params files
na_domain = xr.open_dataset(na_domain_path)
na_params = xr.open_dataset(na_params_path)

#first load in table that has bounds for each HUC-2 or PFAF region
region_bounds = pd.read_csv(region_bounds_path,dtype={'region':'str'})

#list of all HUC-2 or PFAF regions (as strings)
region_list = region_bounds.region.unique()

#specify buffer (use 1/16-degree which is the resolution of the global domain/params files)
grid_buffer = 1./16

#now generate filtered domain and params
for i in range(len(region_list)):
    reg_select = region_list[i]
    min_lon = region_bounds[region_bounds.region==reg_select]['min_lon'].values[0]
    min_lat = region_bounds[region_bounds.region==reg_select]['min_lat'].values[0]
    max_lon = region_bounds[region_bounds.region==reg_select]['max_lon'].values[0]
    max_lat = region_bounds[region_bounds.region==reg_select]['max_lat'].values[0]
       
    #slice domain and params for HUC-02 or PFAF region, with buffer
    na_domain_sel = na_domain.sel(lon=slice(min_lon-grid_buffer,max_lon+grid_buffer),
                                  lat=slice(min_lat-grid_buffer,max_lat+grid_buffer))
                                  
    na_params_sel = na_params.sel(lon=slice(min_lon-grid_buffer,max_lon+grid_buffer),
                                   lat=slice(min_lat-grid_buffer,max_lat+grid_buffer))

    #save results
    na_domain_sel.to_netcdf(save_params_path+'namerica_domain_'+reg_select+'.nc')
    na_params_sel.to_netcdf(save_domain_path+'namerica_params_'+reg_select+'.nc')
    na_domain_sel.close()
    na_params_sel.close()
    
na_domain.close()
na_params.close()

end_time = time.time()
elapsed_time = end_time-start_time
print('Total time taken (seconds): ',elapsed_time)