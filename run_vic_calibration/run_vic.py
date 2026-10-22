#! /usr/bin/env python

import os
import xarray as xr
import pandas as pd
import numpy as np
import sys
from glob import glob
import subprocess
from vic_calibration_constants import *

def run_vic():
    """Function to call VIC exectuable.
    Inputs: None
    Returns: None."""
    # os.system('OMP_NUM_THREADS=1 ./vic_image -g config_calib.txt')
    subprocess.run(['./vic_image.exe', '-g', 'config_calib.txt'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={'OMP_NUM_THREADS': '1', **os.environ})  # vic_image

def read_params():
    """Reads in initial parameter values from vic.in and creates dictionary associating each with the corresponding parameter.
    Inputs: None
    Returns: dictionary params.
    
    Order of input parameters in vic.in:
    <infilt> # Variable infitration parameter
    <Dsmax>  # Max velocity of base flow
    <D_s>    # Fraction of where nonlinear base flow occurs
    <Ws>     # Fraction of maximum soil moisture where non-linear baseflow occurs
    <depth2> # Thickness of soil moisture layer 2
    <depth3> # Thickness of soil moisture layer 3
    <expt2>  # Brooks-Corey baseflow parameter layer 2
    <expt3>  # Brooks-Corey baseflow parameter layer 3
    """
    n_params = 8 #number of parameters being varied
    with open('vic.in', 'r') as f: #read in vic.in
        lines = f.readlines()
    p = [float(line.split('#')[0]) for line in lines[0:n_params]]
    
    params = {} #create empty dictionary and then populate it with parameter values
    params['infilt'] = p[0]
    params['Dsmax'] = p[1]
    params['D_s'] = p[2]
    params['Ws'] = p[3]
    params['depth2'] = p[4]
    params['depth3'] = p[5]
    params['expt2'] = p[6]
    params['expt3'] = p[7]
    
    return params

def modify_params(params):
    """Function to modify VIC input parameters that are being calibrated
    Inputs:
    params: dataframe of parameters values to update netCDF with.  
    Returns: None
    
    #Information about parameters being calibrated (name, initial value, lower bound, upper bound)
    # name       init.      lower    upper
    infilt       0.1     0.001      0.8 
    Dsmax        5.0     1.000     30.0 
    D_s          0.5     0.000      1.0 
    Ws           0.7     0.500      1.0 
    depth2       0.5     0.100      1.0 
    depth3       1.0     0.100      2.0 
    expt2       10.0     8.000     30.0 
    expt3       10.0     8.000     30.0 
    """
    vic_params = xr.open_dataset('params.nc') #open params.nc netcdf file
    #define parameters
    vic_params['infilt'][:, :] = params['infilt']
    vic_params['Dsmax'][:, :] = params['Dsmax']
    vic_params['Ds'][:, :] = params['D_s']
    vic_params['Ws'][:, :] = params['Ws']
    vic_params['depth'][1, :, :] = params['depth2']
    vic_params['depth'][2, :, :] = params['depth3']
    vic_params['expt'][1, :, :] = params['expt2']
    vic_params['expt'][2, :, :] = params['expt3']
    vic_params.to_netcdf('params_updated.nc') #save updated parameters
    return

def nse(obs, pred):
    """Calculates Nash-Sutcliffe Efficiency (NSE) - metric of model performance.
    Inputs:
    obs: 1-d array of observed record.
    pred: 1-d array of predicted values.
    Returns: 
    val: NSE value."""
    val = (1-(np.sum((obs-pred)**2)/np.sum((obs-np.mean(obs))**2)))
    return val


def kge(obs, pred):
    """ Calculates Klein-Gupta Efficiency (KGE) - metric of model performance.
    Inputs:
    obs: 1-d array of observed record.
    pred: 1-d array of predicted values.
    Returns:
    val: KGE value."""
    r = np.corrcoef(pred, obs)[0, 1] #correlation coefficient
    alpha = np.std(pred) / np.std(obs) #relative variance
    beta = np.mean(pred) / np.mean(obs) #relative bias
    gamma = alpha / beta
    val = 1 - np.sqrt((r - 1) ** 2 + (beta - 1) ** 2 + (gamma - 1) ** 2)
    return val


def compute_obj(vic_runoff_file,calib_runoff_file,start_date, end_date):
    """Performs objective function calculation.
    Inputs:
    input_dir: path to runoff calibration dataset
    start_date: start date of calibration period
    end_date: end date of calibration period
    Returns: objective function value."""
    # read VIC output data
    output = xr.open_dataset(vic_runoff_file) # read VIC output data
    runoff_vic = output['OUT_RUNOFF'].isel(lon=0, lat=0) #just runoff, not baseflow when calibration is to USGS quickflow
    # .resample(time='D').sum(['time', 'lat', 'lon'])
    
    # read the concatenated calibration runoff file at once (potentially to increase efficiency)
    runoff_obs = xr.open_dataset(calib_runoff_file)['calib_qf_value'] 
    
    # only compare for the date range of interest - filter both vic and "observed"
    runoff_vic = runoff_vic.sel(time=slice(start_date,end_date))
    runoff_obs = runoff_obs.sel(time=slice(start_date,end_date))
                                
    # compare the monthly SUM statistics
    runoff_vic = runoff_vic.resample(time='ME').sum().to_numpy().ravel() #get monthly sum of the daily values
    runoff_obs = runoff_obs.resample(time='ME').sum().to_numpy().ravel() #convert from m/month to mm/month
    return -kge(runoff_obs, runoff_vic)


def write_output(obj):
    """Write output vic.out.
    Inputs: obj
    Returns: None."""
    f = open('vic.out', 'w') #open vic.out file for writing
    f.write('KGE '+str(obj)+' '+str(obj)+'\n') # ostrich bugs out if there is only one value on a line
    f.close()


if __name__ == '__main__':   
    vic_runoff_file = 'vic_runoff.{yr}-01-01.nc'.format(yr=full_run_start_year)
    calib_runoff_file = 'calib_runoff.nc'
    start_date = np.datetime64(str(calib_start_year)+'-01-01')
    end_date =  np.datetime64(str(calib_end_year)+'-12-31')
    updated_params = read_params() #read parameters
    modify_params(updated_params) #update parameters
    run_vic() #run VIC
    obj = compute_obj(vic_runoff_file,calib_runoff_file,start_date,end_date) #compute objective function
    write_output(obj) #write output