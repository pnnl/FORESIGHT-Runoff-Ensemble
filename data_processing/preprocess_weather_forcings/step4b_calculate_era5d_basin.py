#Abigail Birnbaum (abigail.birnbaum@pnnl.gov)
#Last updated: 2026-10-01
#script to process weather data from ERA-5 downscaled

#import required packages
import os
import sys
import time
import numpy as np
import pandas as pd
import xarray as xr

def calculate_6hr(wd,time_samp='6h'):
    """Method to filter wd (weather data) to region of interest
    Inputs:
    wd = weather data as xarray. Contains the following forcing variables: PRECIP, T2, PSFC, SWDOWN, GLW, VP, and WSPEED
    time_samp = time sampling to use (default 6 hours)
    time_samp = time sampling to use (default 6 hours)
    
    Outputs:
    wd_merge: xarray resampled at desired time_samp.
    """
    #for precip --> take sum; for other variables, take mean
    start_time = wd.time.values[0] #initial time period
    wd_tosum = wd.get(['PRECIP']) #sum for precip
    wd_tosum = wd_tosum.resample(time=time_samp,origin=start_time,label='left').sum()    
    wd_tomean = wd.get(['T2', 'PSFC', 'SWDOWN', 'GLW', 'VP', 'WSPEED']) #mean for temp, pressure, radiation, wind speed
    wd_tomean = wd_tomean.resample(time=time_samp,origin=start_time,label='left').mean()
    # merge sums and means datasets
    wd_merge = xr.merge([wd_tosum, wd_tomean])
    return wd_merge #for leap year - should have length 1464, for non-leap year should have length 1460
   
########################################################################################
####################################### MAIN ###########################################
########################################################################################

#PATHS/VARIABLES THAT MAY CHANGE
pwp = '/gcfs/projects/foresight/hydrology/'
wdp = pwp+'ERA5/downscaled_era5_v3/era5_by_huc2_year/'

#path to save output
save_path = pwp+'ERA5/downscaled_era5_v3/era5_by_basin_year/'

year_list = ['1980','1981','1982','1983','1984','1985','1986','1987','1988','1989',
            '1990','1991','1992','1993','1994','1995','1996','1997','1998','1999',
            '2000','2001','2002','2003','2004','2005','2006','2007','2008','2009',
            '2010','2011','2012','2013','2014','2015','2016','2017','2018','2019',
            '2020','2021','2022','2023','2024','2025'] #46 years
            
reg_list = ['huc01','huc02','huc03','huc04','huc05','huc06','huc07','huc08','huc09',
            'huc10','huc11','huc12','huc13','huc14','huc15','huc16','huc17','huc18',
            'pfaf71','pfaf72','pfaf73','pfaf75','pfaf77','pfaf78']

fract_path_all = pwp+'abirn_vic/input_data/grid_cell_conversions/grid_12km_basin/fract_cells_grid_12km_basin_'
######################### MAIN ###################################

if __name__ == '__main__':
    st = time.time()
    idx = int(sys.argv[1]) #index of year to run
    yr = year_list[idx]
    
    for reg_sel in reg_list:
        
        os.makedirs(save_path+reg_sel+'/',exist_ok=True)
        
        fract_path = fract_path_all+reg_sel+'.csv'
        fract_basins = pd.read_csv(fract_path,dtype={'basin':'str'})
            
        #load in data (already split by huc02 region and year)
        wd = xr.open_dataset(wdp+reg_sel+'/downscaled_era5_12km_'+reg_sel+'_'+yr+'.nc')
        
        #calculate 6-hourly values (gridded)
        wd_merge = calculate_6hr(wd,time_samp='6h')
        
        #rename dimensions/coordinates
        wd_merge = wd_merge.rename({'south_north':'y','west_east':'x'})
        
        #calculate basin-scale forcings (mean across grid cells)
        forcings_df = wd_merge.to_dataframe().reset_index() #convert forcings to dataframe
        merged_df = forcings_df.merge(fract_basins,on=['y','x'])  #merge with fract_basins
    
        #calculate means for forcings
        forc_vars = ['PRECIP','T2','PSFC','SWDOWN','GLW','VP','WSPEED']
        forc_vars_fract = []
        for col in forc_vars:
            merged_df[col+'_fract'] = merged_df[col]*merged_df['fract_basin_area']
            forc_vars_fract.append(col+'_fract')
        #sum across fractions
        merged_df_mean = merged_df.groupby(['time','basin'])[forc_vars_fract].sum().reset_index() #weighted average
        #rename columns
        merged_df_mean = merged_df_mean.rename(columns={'PRECIP_fract':'PRECIP','T2_fract':'T2','PSFC_fract':'PSFC',
                                                    'SWDOWN_fract':'SWDOWN','GLW_fract':'GLW','VP_fract':'VP',
                                                    'WSPEED_fract':'WSPEED'})
        #save as xarray (netcdf)
        merged_ds = merged_df_mean.set_index(['basin','time']).to_xarray()
        
        #save output
        merged_ds.to_netcdf(save_path+reg_sel+'/downscaled_era5_12km_'+reg_sel+'_'+yr+'.nc')
    
        #print
        tvals = merged_ds.time.values
        print(reg_sel+', '+yr)
        print('# time periods: ',len(tvals))
        print('first time period :',tvals[0])
        print('last time period: ',tvals[-1])