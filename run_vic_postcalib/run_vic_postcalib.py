#Abigail Birnbaum
#Calibration - Lumped Basin with new weather data
#Last updated: 2026-06-23

#import packages
import pandas as pd
import xarray as xr
import os
import sys
import shutil
import glob
import subprocess
import time
from datetime import timedelta
import numpy as np
from vic_constants import *
from vic_helper_methods import *

def run_vic(cur_path,working_path,
            basin_select,scenario_name,
            full_run_start_year,full_run_end_year,
            params_path,orig_domain_file,
            orig_forcings_dict,multi_factor_dict,
            fract_cells_0625_file,
            stor_vic_output_runoff):
         
    #set path for basin we're working with
    path_basin = working_path + 'postcalib_'+basin_select+'_'+scenario_name+'/'   
    
    #Create VIC inputs
    fract_cells_grid_0625_basin = pd.read_csv(fract_cells_0625_file,dtype={'basin':'str'})
    basin_xr_0625 = fract_cells_grid_0625_basin[fract_cells_grid_0625_basin.basin==basin_select].filter(
                                            ['lat','lon',
                                            'basin_area_m2',
                                            'grid_0625_area_m2',
                                            'area_in_basin',
                                            'fract_basin_area',
                                            'fract_grid_0625_area']).set_index(['lat','lon']).to_xarray()
                                                                             
    # get list of years to create forcings files for
    full_run_yr_list = np.linspace(full_run_start_year,full_run_end_year,full_run_end_year-full_run_start_year+1)
    full_run_yr_list = full_run_yr_list.astype(int).tolist()
    
    path_input = path_basin+'vic_inputs/'
    os.makedirs(path_input,exist_ok=True)
    
    # load in calibrated params file  
    if not os.path.isfile(path_input+'params_'+basin_select+'_calib.nc'):
        new_params = xr.open_dataset(params_path+'params_'+basin_select+'_calib.nc')
        new_params.to_netcdf(path_input+'params_'+basin_select+'_calib.nc')
    else:
        new_params = xr.load_dataset(path_input+'params_'+basin_select+'_calib.nc')
    avg_lon = new_params['lon'].values[0]; avg_lat = new_params['lat'].values[0]
    
    # does domain file already exist for basin?
    if not os.path.isfile(path_input+'domain_'+basin_select+'.nc'):
        new_domain = create_domain_basin(basin_xr_0625,orig_domain_file,avg_lon,avg_lat)
        new_domain.to_netcdf(path_input+'domain_'+basin_select+'.nc')
        
    # do forcing files exist?
    for yr in full_run_yr_list:
        orig_forcings_file = orig_forcings_dict[scenario_name]+str(yr)+'.nc'
        multi_factor = multi_factor_dict[scenario_name]
        if not os.path.isfile(path_input+'forcings_'+basin_select+'_'+scenario_name+'_'+str(yr)+'.nc'):
            new_forcings = create_forcings_basin(orig_forcings_file,basin_select,avg_lon,avg_lat,multi_factor)
            new_forcings.to_netcdf(path_input+'forcings_'+basin_select+'_'+scenario_name+'_'+str(yr)+'.nc') 
   
    #move all of the files into the subdirectory    
    shutil.copy(cur_path+'vic_image.exe',path_basin)
    shutil.copy(cur_path+'vic_constants.py',path_basin)
    
    #Change directory
    os.chdir(path_basin)
    
    with open('config.txt', 'w') as f:
        f.write(vic_config.format(start_year=full_run_start_year, end_year=full_run_end_year, basin=basin_select,scenario=scenario_name))
           
    ######################## Now actually run VIC ########################   
    subprocess.run(['./vic_image.exe', '-g', 'config.txt'],env={'OMP_NUM_THREADS': '1', **os.environ},
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # vic_image    
    ##move final VIC run to appropriate save directory
    vic_runoff_output = 'vic_runoff.{yr}-01-01.nc'.format(yr=full_run_start_year)
    stor_scenario = stor_vic_output_runoff+scenario_name+'/'
    os.makedirs(stor_scenario,exist_ok=True)
    shutil.copy(vic_runoff_output,stor_scenario+'vic_runoff_{basin}_{scenario}_{yr}-01-01.nc'.format(basin=basin_select,scenario=scenario_name,yr=full_run_start_year))

    ##delete entire path_basin directory
    shutil.rmtree(path_basin)

    return
    
if __name__ == '__main__':
    
    idx = int(sys.argv[1])-1
    
    if idx < len(basin_scenario_pairs):    
        basin_select = basin_scenario_pairs[idx][0]
        scenario_name = basin_scenario_pairs[idx][1]

        #check to see if file already exists - if so, break 
        final_file_path = stor_vic_output_runoff+scenario_name+'/vic_runoff_{basin}_{scenario}_{yr}-01-01.nc'.format(basin=basin_select,scenario=scenario_name,yr=full_run_start_year)
        if os.path.exists(final_file_path):
            print(basin_select+', '+scenario_name+': already complete')
            
        else:
            start_time = time.time()  
            run_vic(cur_path,working_path,
                basin_select,scenario_name,
                full_run_start_year,full_run_end_year,
                params_path,orig_domain_file,
                orig_forcings_dict,multi_factor_dict,
                fract_cells_0625_file,
                stor_vic_output_runoff)
                            
            end_time = time.time()
            print(basin_select+', '+scenario_name+': elapsed time (seconds): ',end_time-start_time)
        
    else:
        print('no basin to calibrate')