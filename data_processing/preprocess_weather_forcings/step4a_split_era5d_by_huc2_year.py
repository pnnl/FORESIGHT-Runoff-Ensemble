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

def filter_to_region(wd,xvals,yvals,crs_proj,reg_bounds):
    """Method to filter wd (weather data) to region of interest
    Inputs:
    wd = weather data as xarray
    xvals = coordinates in south-north/lon direction (projected coordinate system)
    yvals = coordinates in west-east/lat direction (projected coordinate system)
    crs_proj = projected coordinate system that wdf is in
    reg_bounds = boundaries of region (in projected coordinate system)

    Outputs:
    wd: xarray filtered to region of interest
    """

    #load in weather data file for given day
    wd = wd.drop_vars(['XLONG','XLAT']) #drop XLONG, XLAT coordinates
    wd = wd.assign_coords(west_east=('west_east',xvals)) #assign west_east as coordinate in addition to dims
    wd = wd.assign_coords(south_north=('south_north',yvals)) #assign south_north as coordinate in addition to dims
    wd = wd.rio.write_crs(crs_proj).rio.set_spatial_dims(x_dim='west_east',y_dim='south_north').rio.write_coordinate_system() #set CRS

    #filter to region of interest
    wd = wd.sel(south_north=slice(reg_bounds[1],reg_bounds[3]),west_east=slice(reg_bounds[0],reg_bounds[2]))

    return wd

def generate_vic_forcings(wd):    
    """
    Method to process weather variables needed by VIC hydro model
    Inputs:
    wd = weather data as xarray
    
    Outputs:
    wd = xarray with variables T2 (temp), WSPEED (wind speed), PRECIP (accumulated precip), 
    # VP (vapor pressure), PSFC (atmospheric pressure) in proper units
    """
    
    #now process variables
    #for total precipitation, add units/description
    wd['PRECIP'] = wd['PREC_ACC_NC'].copy(deep=True)
    wd.PRECIP.attrs['units'] = 'mm'
    wd.PRECIP.attrs['description'] = 'Total Precipitation'
    
    #compute wind speed from component winds
    wd = wd.assign(WSPEED = np.sqrt(wd['U10']**2 + wd['V10']**2))
    wd.WSPEED.attrs['units'] = 'm s-1'
    wd.WSPEED.attrs['description'] = 'WIND SPEED at 10 M'
    
    #compute vapor pressure
    wd = wd.assign(VP = (wd['Q2'] * wd['PSFC'])/(0.622 + wd['Q2']))
    wd.VP.attrs['units'] = 'Pa'
    wd.VP.attrs['description'] = 'VAPOR PRESSURE'
    
    #air temperature K to C
    wd['T2'] = wd['T2'] - 273.15
    wd.T2.attrs['units'] = 'C'
    
    #atmospheric pressure Pa to kPa
    wd['PSFC'] = wd['PSFC']/1000
    wd.PSFC.attrs['units'] = 'kPa'
    
    #vapor pressure Pa to kPa
    wd['VP'] = wd['VP']/1000
    wd.VP.attrs['units'] = 'kPa'

    #just keep variables that we want
    wd = wd.get(['T2', 'PSFC', 'SWDOWN', 'GLW', 'VP', 'WSPEED','PRECIP'])
    
    #make sure all data is in float32 
    wd[['T2', 'PSFC', 'SWDOWN', 'GLW', 'VP', 'WSPEED','PRECIP']] = wd[['T2', 'PSFC', 'SWDOWN', 'GLW', 'VP', 'WSPEED','PRECIP']].astype('float32')
    
    return wd     
   
############################################
################# MAIN #####################
############################################

#PATHS/VARIABLES THAT MAY CHANGE
#directory that contains weather data - dates currently available in folder 2007-01-01 to 2013-12-31
pwp = '/gcfs/projects/foresight/hydrology/' #parent working path
wdp = pwp+'ERA5/downscaled_era5_v3/downscaled_era5_v3/' #folder containing weather data (wdp = weather data path)

#path to save output
save_path = pwp+'ERA5/downscaled_era5_v3/era5_by_huc2_year/'

#PATHS/VARIABLES THAT LIKELY WON'T CHANGE
#path to ncar region boundaries (in projected crs)
ncar_reg_bounds_file = pwp+'abirn_vic/input_data/extra_spatial_data/region_bounds.csv'

#same projected coordinate system as TGW (lambert conformal conic)
crs_proj = '+proj=lcc +lat_0=40.0000076293945 +lon_0=-97 +lat_1=30 +lat_2=45 +x_0=0 +y_0=0 +R=6370000 +units=m +no_defs'
#ASSUME coordinate system is same as TGW data (424 lons x 299 lats - lambert conformal conic - https://tgw-data.msdlive.org/)
#create array of x-coordinates (based on TGW data, 424 rows)
nx = 424
start_x = -2538000.0 #min lon value
res_x = 12000.0 #12 km resolution
xvals = np.arange(start_x,start_x+(nx*res_x),res_x)
#create array of y-coordinates (based on TGW data, 299 columns)
ny = 299
start_y = -1788000.0 #min lat value
res_y = 12000.0 #12 km resolution
yvals = np.arange(start_y,start_y+(ny*res_y),res_y)

#select region and get region bounds
all_reg_bounds = pd.read_csv(ncar_reg_bounds_file)

year_list = ['1980','1981','1982','1983','1984','1985','1986','1987','1988','1989',
            '1990','1991','1992','1993','1994','1995','1996','1997','1998','1999',
            '2000','2001','2002','2003','2004','2005','2006','2007','2008','2009',
            '2010','2011','2012','2013','2014','2015','2016','2017','2018','2019',
            '2020','2021','2022','2023','2024','2025'] #46 years

reg_list = ['huc01','huc02','huc03','huc04','huc05','huc06','huc07','huc08','huc09',
            'huc10','huc11','huc12','huc13','huc14','huc15','huc16','huc17','huc18',
            'pfaf71','pfaf72','pfaf73','pfaf75','pfaf77','pfaf78']

######################### MAIN ###################################

if __name__ == '__main__':
    
    st = time.time()
    idx = int(sys.argv[1]) #index of year to run
    yr = year_list[idx]
    #get list of file names
    date_list = pd.date_range(start=yr+'-01-01',end=yr+'-12-31',freq='D').date.astype(str) 
    file_list = wdp+'era5_downscaled_'+date_list+'.nc'
    
    #read in files
    ds = xr.open_mfdataset(file_list)
    n = len(ds['time'].values)
    ds = ds.chunk({'time':n})
    
    for reg_sel in reg_list:
        #path to save output
        os.makedirs(save_path+reg_sel,exist_ok=True)

        reg_sel_bounds = all_reg_bounds[all_reg_bounds.region==reg_sel]
        reg_sel_bounds = reg_sel_bounds.filter(['min_lon_weather','min_lat_weather','max_lon_weather','max_lat_weather']).to_numpy().ravel()
        reg_sel_bounds[0] = reg_sel_bounds[0] - res_x
        reg_sel_bounds[1] = reg_sel_bounds[1] - res_y
        reg_sel_bounds[2] = reg_sel_bounds[2] + res_x
        reg_sel_bounds[3] = reg_sel_bounds[3] + res_y
        
        #filter region + get forcing variables (hourly)
        ds_filt = filter_to_region(ds,xvals,yvals,crs_proj,reg_sel_bounds) #filter to region
        ds_forc = generate_vic_forcings(ds_filt) #get variables of interest

        #save as netCDF
        ds_forc.to_netcdf(save_path+reg_sel+'/'+'downscaled_era5_12km_'+reg_sel+'_'+yr+'.nc')
        
        #print
        tvals = ds_forc.time.values
        print(reg_sel+', '+yr)
        print('# time periods: ',len(tvals))
        print('first time period :',tvals[0])
        print('last time period: ',tvals[-1])