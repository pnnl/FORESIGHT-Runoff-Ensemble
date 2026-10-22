#Abigail Birnbaum
#script to process weather data from ERA-5 downscaled (12 km)
#Last updated: 2026-07-01

#import required packages
import os
import sys
import time
import numpy as np
import pandas as pd
import xarray as xr
from itertools import product
import joblib

##########################################################################################################################################
################################################################ Methods #################################################################
##########################################################################################################################################

def load_vic(data_path,filename,scen_name):
    bs = filename.split('_')[2]
    ds = xr.open_dataset(data_path+filename) #load in data
    #convert to dataframe
    bs_df = ds[['OUT_RUNOFF','OUT_BASEFLOW']].to_dataframe().reset_index().drop(columns=['lat','lon']).rename(columns={'OUT_RUNOFF':'vic_qf',
                                                                                                                       'OUT_BASEFLOW':'vic_bf'})
    bs_df_month = bs_df.set_index('time')[['vic_qf','vic_bf']].resample('MS').sum().reset_index()
    bs_df['basin'] = bs
    bs_df_month['basin'] = bs
    bs_df['scenario'] = scen_name
    bs_df_month['scenario'] = scen_name
    return bs_df, bs_df_month


##########################################################################################################################################
################################################################ Constants ###############################################################
##########################################################################################################################################

#path for output data
output_dp = '/gcfs/projects/foresight/hydrology/abirn_vic/run_vic_postcalib/vic_output/vic_runoff_output/'

#path to save processed runoff output
save_dp = '/gcfs/projects/foresight/hydrology/abirn_vic/final_vic_output/'

#reg_list = ['huc01','huc02','huc03','huc04','huc05','huc06','huc07','huc08','huc09',#'huc10','huc11','huc12','huc13','huc14','huc15','huc16','huc17','huc18',
#'pfaf71','pfaf72','pfaf73','pfaf75','pfaf77','pfaf78']

#scenario_list = ['era5d','ic0_fhist','ic1_fhist','ic2_fhist','ic3_fhist','ic4_fhist',#'ic5_fhist','ic6_fhist','ic7_fhist','ic8_fhist','ic9_fhist']

reg_list = ['huc04','huc05','huc13']

scenario_list = ['era5d']

#region, scenario pairs
reg_scenario_pairs = list(product(reg_list, scenario_list))

##########################################################################################################################################
################################################################### Main #################################################################
##########################################################################################################################################
    
if __name__ == '__main__':
    
    idx = int(sys.argv[1])
    
    reg_sel = reg_scenario_pairs[idx][0]
    scen_name = reg_scenario_pairs[idx][1]
    print(reg_sel)
    print(scen_name)
    
    output_dp_scen = output_dp +reg_sel+'/'+scen_name+'/' #path to outputs for scenario
    vic_output_files = os.listdir(output_dp_scen)
    
    save_dp_scen = save_dp+reg_sel+'/'
    os.makedirs(save_dp_scen,exist_ok=True)
            
    vic_res = joblib.Parallel(n_jobs=64)(joblib.delayed(load_vic)(output_dp_scen, vic_output_files[i],scen_name) for i in range(len(vic_output_files)))            
    daily_vic = [pair[0] for pair in vic_res]
    monthly_vic = [pair[1] for pair in vic_res]

    #combine into one dataframe
    daily_vic = pd.concat(daily_vic, ignore_index=True)
    monthly_vic = pd.concat(monthly_vic, ignore_index=True)            
                    
    #save csv
    #daily_vic.to_csv(save_vic_path+'daily_vic_'+reg_sel+'.csv',index=False)
    #monthly_vic.to_csv(save_vic_path+'monthly_vic_'+reg_sel+'.csv',index=False)
    
    #save netcdf
    daily_vic_nc = daily_vic.set_index(['basin','time','scenario']).to_xarray()
    daily_vic_nc.to_netcdf(save_dp_scen+'daily_vic_'+reg_sel+'_'+scen_name+'.nc')
    monthly_vic_nc = monthly_vic.set_index(['basin','time','scenario']).to_xarray()
    monthly_vic_nc.to_netcdf(save_dp_scen+'monthly_vic_'+reg_sel+'_'+scen_name+'.nc')
    
    print('Done consolidating files for '+reg_sel + ', '+scen_name)