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
import joblib
import run_vic
from vic_calibration_constants import *
from calibration_methods import *

def run_calibration(cur_path,working_path,basin_select,
                    calib_start_year,calib_end_year,full_run_start_year,full_run_end_year,
                    orig_params_file,orig_domain_file,orig_forcings_path,orig_runoff_file,
                    fract_cells_0625_file,
                    stor_vic_output_runoff,stor_vic_output_params,stor_calib_process):
    
    #set path for basin we're working with
    path_basin = working_path + 'calib_'+basin_select+'/'   
    os.makedirs(path_basin, exist_ok=True) 
    
    #### CREATE VIC INPUTS ####
    fract_cells_grid_0625_basin = pd.read_csv(fract_cells_0625_file,dtype={'basin':'str'})
    basin_xr_0625 = fract_cells_grid_0625_basin[fract_cells_grid_0625_basin.basin==basin_select].filter(
                                            ['lat','lon',
                                            'basin_area_m2',
                                            'grid_0625_area_m2',
                                            'area_in_basin',
                                            'fract_basin_area',
                                            'fract_grid_0625_area']).set_index(['lat','lon']).to_xarray()                           
    # get list of years to create forcings and runoff files for    
    full_run_yr_list = np.linspace(full_run_start_year,calib_end_year,calib_end_year-full_run_start_year+1)
    full_run_yr_list = full_run_yr_list.astype(int).tolist()
    
    path_input = path_basin+'vic_inputs/'
    os.makedirs(path_input,exist_ok=True)
    
    # does params file already exist for basin?
    if not os.path.isfile(path_input+'params_'+basin_select+'.nc'):
        #print('creating params file for basin '+basin_select)
        new_params = create_params_basin(basin_xr_0625,orig_params_file)
        new_params.to_netcdf(path_input+'params_'+basin_select+'.nc')
    else:
        #print('basin '+basin_select+' params file already exists')
        new_params = xr.load_dataset(path_input+'params_'+basin_select+'.nc')
    avg_lon = new_params['lon'].values[0]; avg_lat = new_params['lat'].values[0]
    
    # does domain file already exist for basin?
    if not os.path.isfile(path_input+'domain_'+basin_select+'.nc'):
        #print('creating domain file for basin '+basin_select)
        new_domain = create_domain_basin(basin_xr_0625,orig_domain_file,avg_lon,avg_lat)
        new_domain.to_netcdf(path_input+'domain_'+basin_select+'.nc')
    #else:
        #print('basin '+basin_select+' domain file already exists')
    
    # do forcing files exist?
    for yr in full_run_yr_list:
        orig_forcings_file = orig_forcings_path+str(yr)+'.nc'
        if not os.path.isfile(path_input+'forcings_'+basin_select+'_'+str(yr)+'.nc'):
            #print('creating forcings file for basin '+basin_select+' year: '+str(yr))
            new_forcings = create_forcings_basin(orig_forcings_file,basin_select,avg_lon,avg_lat)
            new_forcings.to_netcdf(path_input+'forcings_'+basin_select+'_'+str(yr)+'.nc')
        #else:
            #print('forcings file for basin '+basin_select+' year '+str(yr)+' already exists')    
                
    # do runoff calibration files exist?
    if not os.path.isfile(path_input+'calib_runoff_'+basin_select+'.nc'):
        #print('creating calibration runoff file for basin '+basin_select)
        calib_runoff = xr.open_dataset(orig_runoff_file).sel(basin=basin_select,time=slice(str(calib_start_year)+'-01-01',
                                                                                           str(calib_end_year)+'-12-31'))
        calib_runoff.to_netcdf(path_input+'calib_runoff_'+basin_select+'.nc')
    #else:
        #print('calibration runoff file for '+basin_select+' already exists')
          
    #move all of the files into the subdirectory    
    #copy files and give them generic names
    shutil.copy(path_input+'params_'+basin_select+'.nc',path_basin+'params.nc') #original params file
    shutil.copy(path_input+'params_'+basin_select+'.nc',path_basin+'params_updated.nc') #params file that actually gets read in by VIC and updated
    shutil.copy(cur_path+'/vic_image.exe',path_basin)
    shutil.copy(cur_path+'/vic_calibration_constants.py',path_basin)
    
    #files relevant to calibration:
    shutil.copy(path_input+'calib_runoff_'+basin_select+'.nc',path_basin+'calib_runoff.nc') #calibration file (runoff)
    shutil.copy(cur_path+'/vic.in.tpl',path_basin)
    shutil.copy(cur_path+'/run_vic.py',path_basin)
    shutil.copy(cur_path+'/OstrichGCC',path_basin)
    
    #Change directory
    os.chdir(path_basin)
    
    # Specify initial values for calibration
    p = []
    with xr.load_dataset(path_basin+'params.nc') as ds:
        for s in ['infilt', 'Dsmax', 'Ds', 'Ws', 'depth2', 'depth3', 'expt2', 'expt3']:
            if s.startswith('depth'):
                p.append(float(ds['depth'].isel(lon=0, lat=0, nlayer=int(s[-1]) - 1)))
            elif s.startswith('expt'):
                p.append(float(ds['expt'].isel(lon=0, lat=0, nlayer=int(s[-1]) - 1)))
            else:
                p.append(float(ds[s].isel(lon=0, lat=0)))

    # if plim_ctr has percent(%) strings to constrain the upper and lower limits of calibration parameters
    plim = plim_ctr.copy()
    for i, arr in enumerate(plim):
        if isinstance(arr[0], str) and arr[0].endswith('%'):
            plim[i][0] = p[i] * (1 + int(arr[0][:-1]) / 100)
        if isinstance(arr[1], str) and arr[1].endswith('%'):
            plim[i][1] = p[i] * (1 + int(arr[1][:-1]) / 100)

    vic_in = f'''\
    {p[0]:0.4f} # Variable infitration parameter
    {p[1]:0.4f} # Max velocity of base flow
    {p[2]:0.4f} # Fraction of where nonlinear base flow occurs
    {p[3]:0.4f} # Fraction of maximum soil moisture where non-linear baseflow occurs
    {p[4]:0.4f} # Thickness of soil moisture layer 2
    {p[5]:0.4f} # Thickness of soil moisture layer 3
    {p[6]:0.4f} # Brooks-Corey baseflow parameter layer 2
    {p[7]:0.4f} # Brooks-Corey baseflow parameter layer 3
    '''

    # "ostIn.txt" will have the initial values from VICGlobal
    ostIn_txt = f'''\
    ProgramType DDS
    ObjectiveFunction  GCOP
    ModelExecutable  ./run_vic.py

    BeginFilePairs
    vic.in.tpl ; vic.in
    EndFilePairs

    BeginExtraFiles
    params.nc
    config.txt
    vic_image.exe
    EndExtraFiles

    BeginParams
    # name       init.      lower       upper       transformations
    <infilt>  {p[0]:0.5f}   {plim[0][0]:0.5f}   {plim[0][1]:0.5f}   none   none   none
    <Dsmax>   {p[1]:0.5f}   {plim[1][0]:0.5f}   {plim[1][1]:0.5f}   none   none   none
    <D_s>     {p[2]:0.5f}   {plim[2][0]:0.5f}   {plim[2][1]:0.5f}   none   none   none
    <Ws>      {p[3]:0.5f}   {plim[3][0]:0.5f}   {plim[3][1]:0.5f}   none   none   none
    <depth2>  {p[4]:0.5f}   {plim[4][0]:0.5f}   {plim[4][1]:0.5f}   none   none   none
    <depth3>  {p[5]:0.5f}   {plim[5][0]:0.5f}   {plim[5][1]:0.5f}   none   none   none
    <expt2>   {p[6]:0.5f}   {plim[6][0]:0.5f}   {plim[6][1]:0.5f}   none   none   none
    <expt3>   {p[7]:0.5f}   {plim[7][0]:0.5f}   {plim[7][1]:0.5f}   none   none   none
    EndParams

    BeginResponseVars
    # name  filename  ; keyword   skip_lines  col token
    KGE  vic.out   ; KGE                0    2   ' ' 
    EndResponseVars

    BeginConstraints
    EndConstraints

    BeginGCOP
    CostFunction KGE
    PenaltyFunction APM
    EndGCOP

    BeginInitParams  
    {p[0]:0.4f} {p[1]:0.4f} {p[2]:0.4f} {p[3]:0.4f} {p[4]:0.4f} {p[5]:0.4f} {p[6]:0.4f} {p[7]:0.4f}
    EndInitParams

    BeginDDS
    PerturbationValue      0.5
    MaxIterations          100
    UseInitialParamValues
    EndDDS
    '''
    
    # write the files specific to each cell
    with open('vic.in', 'w') as f:
        f.write(vic_in)
    with open('ostIn.txt', 'w') as f:
        f.write(ostIn_txt)
    with open('config_calib.txt', 'w') as f:
        f.write(vic_config.format(start_year=full_run_start_year, end_year=calib_end_year, basin=basin_select))
   
    ######################## Now actually run VIC ########################

    ########################### calibration ###########################
    #print('calibration VIC run for '+basin_select)
    subprocess.run(['./OstrichGCC', '>', '/dev/null'],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # make sure the param file is updated
    params = run_vic.read_params()
    run_vic.modify_params(params)
    
    ######################## post-calibration ########################
    #print('post-calibration VIC final run for '+basin_select)
    #subprocess.run(['./vic_image.exe', '-g', 'config.txt'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,env={'OMP_NUM_THREADS': '1', **os.environ})
    
    ######################## clean-up of directory, only save relevant files ########################
    #move final VIC run to appropriate save directory
    #vic_runoff_postcalib = 'vic_runoff.{yr}-01-01.nc'.format(yr=full_run_start_year)
    #shutil.copy(vic_runoff_postcalib,stor_vic_output_runoff+'vic_runoff_{basin}_{yr}-01-01_calib.nc'.format(basin=basin_select,yr=full_run_start_year))
    shutil.copy('params_updated.nc',stor_vic_output_params+'params_{basin}_calib.nc'.format(basin=basin_select)) #updated params
    
    #save Ostrich output
    shutil.copy('OstOutput0.txt',stor_calib_process+'OstOutput0_{basin}.txt'.format(basin=basin_select))
    
    #delete path_basin directory
    shutil.rmtree(path_basin)
    
    return
    
if __name__ == '__main__':
    
    idx = int(sys.argv[1])-1
    
    if idx < len(basin_list):
        basin_select = str(basin_list[idx])
        #check to see if calibration has already happened
        calib_progress_file = stor_calib_process+'OstOutput0_'+basin_select+'.txt'
        if os.path.exists(calib_progress_file):
            print('calibration already complete for '+str(basin_select))
        else:     
            start_time = time.time()
            run_calibration(cur_path, working_path,basin_select,
                            calib_start_year,calib_end_year,full_run_start_year,full_run_end_year,
                            orig_params_file,orig_domain_file,orig_forcings_path,orig_runoff_file,
                            fract_cells_0625_file,
                            stor_vic_output_runoff,stor_vic_output_params,stor_calib_process)
                            
            end_time = time.time()
            print(basin_list[idx]+': elapsed time (seconds): ',end_time-start_time)
        
    else:
        print('no basin to calibrate')