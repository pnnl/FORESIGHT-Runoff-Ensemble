#Abigail Birnbaum (abigail.birnbaum@pnnl.gov)
#Last updated: 2026-10-01
#script to process weather data from ACE2 downscaled

#import required packages
import os
import sys
import time
import numpy as np
import pandas as pd
import xarray as xr
import rasterio as rio
import rioxarray as rxr

########################################################################################
################################### Define Variables ###################################
########################################################################################

#scenario name
scenario_list = ['ic0_fhist','ic1_fhist','ic2_fhist','ic3_fhist','ic4_fhist',
                'ic5_fhist','ic6_fhist','ic7_fhist','ic8_fhist','ic9_fhist']

year_list = ['1980','1981','1982','1983','1984','1985','1986','1987','1988','1989',
             '1990','1991','1992','1993','1994','1995','1996','1997','1998','1999',
             '2000','2001','2002','2003','2004','2005','2006','2007','2008','2009',
             '2010','2011','2012','2013','2014','2015','2016','2017','2018','2019',
             '2020','2021','2022','2023','2024']
                 
reg_list = ['huc01','huc02','huc03','huc04','huc05','huc06','huc07','huc08','huc09',
            'huc10','huc11','huc12','huc13','huc14','huc15','huc16','huc17','huc18',
            'pfaf71','pfaf72','pfaf73','pfaf75','pfaf77','pfaf78']            
 
##############################################################################################################
#################################################### MAIN ####################################################
##############################################################################################################

if __name__ == '__main__':
    st = time.time()
    idx = int(sys.argv[1]) #index of year to run
    yr = year_list[idx]
    
    for reg_sel in reg_list:
        
        #directory that contains weather data - dates currently available in folder 2007-01-01 to 2013-12-31
        pwp = '/gcfs/projects/foresight/hydrology/'
        wdp = pwp+'ACE2/ACE2_downscaled_v3/ace2_by_huc2_year/'+reg_sel+'/'

        #path to save output
        save_path = pwp+'ACE2/ACE2_downscaled_v3/ace2_by_basin_year/'+reg_sel+'/'
        os.makedirs(save_path,exist_ok=True)

        #load in grid cell fractions
        fract_path = pwp+'abirn_vic/input_data/grid_cell_conversions/grid_12km_basin/fract_cells_grid_12km_basin_'+reg_sel+'.csv'
        fract_basins = pd.read_csv(fract_path,dtype={'basin':'str'})
    
        for scenario_name in scenario_list:
        
            #load in data (split by huc02 region and year)
            wd = xr.open_dataset(wdp+scenario_name+'/ACE2_noise_08_'+reg_sel+'_'+scenario_name+'_'+yr+'.nc') #data is already in 6 hour segments
                    
            #rename dimensions/coordinates
            wd = wd.rename({'south_north':'y','west_east':'x'})
            
            #calculate basin-scale forcings (mean across grid cells)
            forcings_df = wd.to_dataframe().reset_index() #convert forcings to dataframe
            merged_df = forcings_df.merge(fract_basins,on=['y','x'])  #merge with fract_basins
            
            #calculate means for forcings
            forc_vars = ['PRECIP','T2','PSFC','SWDOWN','GLW','VP','WSPEED']
            forc_vars_fract = []
            for col in forc_vars:
                merged_df[col+'_fract'] = merged_df[col]*merged_df['fract_basin_area']
                forc_vars_fract.append(col+'_fract')
            #sum across fractions
            merged_df_mean = merged_df.groupby(['time','basin'])[forc_vars_fract].sum().reset_index()
            #rename columns
            merged_df_mean = merged_df_mean.rename(columns={'PRECIP_fract':'PRECIP','T2_fract':'T2','PSFC_fract':'PSFC',
                                                        'SWDOWN_fract':'SWDOWN','GLW_fract':'GLW','VP_fract':'VP',
                                                        'WSPEED_fract':'WSPEED'})
            #save as xarray (netcdf)
            merged_ds = merged_df_mean.set_index(['basin','time']).to_xarray()
            
            #save output
            os.makedirs(save_path+scenario_name+'/',exist_ok=True)
            merged_ds.to_netcdf(save_path+scenario_name+'/ACE2_noise_08'+'_'+reg_sel+'_'+scenario_name+'_'+yr+'.nc')
            
            #print
            tvals = merged_ds.time.values
            print(reg_sel+', '+scenario_name+', '+yr)
            print('# time periods: ',len(tvals))
            print('first time period :',tvals[0])
            print('last time period: ',tvals[-1])