import xarray as xr
import os
import time
import numpy as np
import pandas as pd

def create_params_basin(basin_xr,orig_params_file):
    """Function to create parameters file at the HUC-12 basin scale.
    Inputs:
    basin_xr: xarray containing grid cells for huc-12 of interest (basin_select)
    orig_param_file: original parameter file contaning HUC-2 region we're looking at.
    basin_select: HUC-12 we want to filter data for
    Outputs:"""

    #get boundaries of huc-12
    min_lon = basin_xr['lon'].values.min(); max_lon = basin_xr['lon'].values.max();
    min_lat = basin_xr['lat'].values.min(); max_lat = basin_xr['lat'].values.max();
    
    in_params = xr.open_dataset(orig_params_file)
    #first let's clean up the params file and combine with basin_xr
    params_basin = in_params.sel(lat=slice(min_lat,max_lat),lon=slice(min_lon,max_lon)).load() #slice params file
    params_basin = xr.combine_by_coords([params_basin,basin_xr],data_vars='minimal') #combine with basin_xr
        
    #there are some grid cells that have NaN for all vegetation classes - assume that these grid cells are open water 
    #(based on visual inspection of these cells in HUC02 + HUC15 level-2 regions) - set veg_class 1 to have Cv = 1. Keep 
    #all other veg_class as Cv NaN.
    #first identify any grid cells that have Cv of NaN for all 
    dv = 'Cv'
    #find basins where all Cv are NaN --> identify this as open water, set Cv = 1 for veg_class 1
    params_basin.sel(veg_class=1)['Cv'][:] = params_basin.sel(veg_class=1)['Cv'].where(params_basin['Cv'].sum('veg_class')!=0,1)
    
    #now, identify which dimensions are used to define each data variable
    #which dimensions are used to define the data variables?
    dim_nl = ['nlayer'] #only nlayer
    pvars_nl = ['layer'] #parameters that vary with nlayer
    dim_ll = ['lat','lon'] #only lat and lon
    pvars_ll = ['mask', 'lons', 'lats', 'infilt', 'Ds', 'Dsmax', 'Ws', 'c', 'elev', 'avg_T', 'dp', 'off_gmt','rough', 'snow_rough', 'annual_prec',
             'July_Tavg', 'cellnum', 'run_cell', 'gridcell', 'fs_active', 'Nveg'] #parameters that vary with lat, lon
    dim_vc_ll = ['veg_class'] #veg class IN ADDITION to lat and lon
    pvars_vc_ll = ['overstory', 'Cv', 'rarc', 'rmin', 'wind_h', 'RGL', 'rad_atten', 'wind_atten', 'trunk_ratio'] #parameters that vary with veg_class, lat, lon
    dim_nl_ll = ['nlayer'] #nlayer in addition to lat and lon
    pvars_nl_ll = ['expt','Ksat', 'phi_s', 'init_moist', 'depth', 'bubble', 'quartz', 'bulk_density', 
             'soil_density', 'Wcr_FRACT', 'Wpwp_FRACT', 'resid_moist', ] #parameters that vary with nlayer, lat, lon
    dim_sb_ll = ['snow_band'] #snow band in addition to lat and lon
    pvars_sb_ll = ['AreaFract', 'elevation', 'Pfactor'] #parameters that vary with snow_band, lat, lon
    dim_vc_rz_ll = ['veg_class','root_zone'] #veg class and root zone in addition to lat and lon
    pvars_vc_rz_ll = ['root_depth','root_fract'] #parameters that vary with veg_class, root_zone, lat, lon
    dim_vc_mo_ll = ['veg_class','month'] #veg class and month in addition to lat and lon
    pvars_vc_mo_ll = ['LAI', 'albedo', 'veg_rough', 'displacement', 'fcanopy'] #parameters that vary with veg_class, month, lat, lon
    
    weight_list = ['basin_area_m2','grid_0625_area_m2','fract_basin_area','fract_grid_0625_area']
           
    # PARAMTERS THAT ONLY VARY WITH NLAYER
    params_basin_nl = params_basin[pvars_nl]
    
    # CREATE XARRAY FOR VARIABLES THAT VARY WITH LAT/LON
    params_basin_ll = params_basin.copy() #copy dataframe
    for dv in pvars_ll: #loop through all of the data variables that vary by lat/lon
        params_basin_ll[dv] = params_basin_ll[dv]*params_basin_ll['fract_basin_area'] #update the values by multiply by fractional basin area
    params_basin_ll_sum = params_basin_ll[pvars_ll].sum() #weighted average by summing up the fractions
    avg_lat = params_basin_ll_sum['lats'].values #get latitude
    avg_lon = params_basin_ll_sum['lons'].values #get longitude
    #create new x-array to store results
    params_basin_ll_combo = xr.Dataset(coords = dict(lat=('lat',[avg_lat]),
                      lon=('lon',[avg_lon])))
    data_vars_list = list(params_basin_ll_sum.data_vars)
    for dv in data_vars_list:
        params_basin_ll_combo[dv] = (('lat','lon'),np.expand_dims(np.expand_dims(params_basin_ll_sum[dv],0),1))
    params_basin_ll_combo['mask'][:] = np.minimum(1,np.ceil(params_basin_ll_combo['mask'].values)) #max value of 1
    params_basin_ll_combo['run_cell'][:] = np.minimum(1,np.ceil(params_basin_ll_combo['run_cell'].values))  # max value of 1
    params_basin_ll_combo['fs_active'][:] = np.minimum(1,np.ceil(params_basin_ll_combo['fs_active'].values)) #max value of 1
    
    #PARAMTERS THAT VARY WITH VEG_CLASS, LAT, LON
    params_basin_vc_ll = params_basin[pvars_vc_ll+weight_list]
    for dv in pvars_vc_ll: #loop through all of the data variables that vary by lat/lon
        params_basin_vc_ll[dv] = params_basin_vc_ll[dv]*params_basin_vc_ll['fract_basin_area'] #update the values by multiply by fractional basin area
    params_basin_vc_ll_sum = params_basin_vc_ll.sum(dim=('lat','lon'),min_count=1)
    params_basin_vc_ll_sum = params_basin_vc_ll_sum[pvars_vc_ll]
    
    #PARAMETERS THAT VARY WITH SNOW_BAND, LAT, LON
    params_basin_sb_ll = params_basin[pvars_sb_ll+weight_list]
    for dv in pvars_sb_ll: #loop through all of the data variables that vary by lat/lon
        params_basin_sb_ll[dv] = params_basin_sb_ll[dv]*params_basin_sb_ll['fract_basin_area'] #update the values by multiply by fractional basin area
    params_basin_sb_ll_sum = params_basin_sb_ll.sum(dim=('lat','lon'),min_count=1)
    params_basin_sb_ll_sum = params_basin_sb_ll_sum[pvars_sb_ll]
    
    #PARAMETERS THAT VARY WITH nlayer, LAT, LON
    params_basin_nl_ll = params_basin[pvars_nl_ll+weight_list]
    for dv in pvars_nl_ll: #loop through all of the data variables that vary by lat/lon
        params_basin_nl_ll[dv] = params_basin_nl_ll[dv]*params_basin_nl_ll['fract_basin_area'] #update the values by multiply by fractional basin area
    params_basin_nl_ll_sum = params_basin_nl_ll.sum(dim=('lat','lon'),min_count=1)
    params_basin_nl_ll_sum = params_basin_nl_ll_sum[pvars_nl_ll]
    
    #PARAMETERS THAT VARY WITH veg_class, month, LAT, LON --> set as maximum value across specified veg_class and month
    params_basin_vc_mo_ll = params_basin.copy()
    params_basin_vc_mo_ll['update_mask'] = np.ceil(params_basin_vc_mo_ll['fract_basin_area'])
    params_basin_vc_mo_ll = params_basin_vc_mo_ll[pvars_vc_mo_ll+['update_mask']]
    for dv in pvars_vc_mo_ll:
        params_basin_vc_mo_ll[dv] = params_basin_vc_mo_ll[dv]*params_basin_vc_mo_ll['update_mask']
    params_basin_vc_mo_ll_max = params_basin_vc_mo_ll.max(dim=('lat','lon'))
    params_basin_vc_mo_ll_max = params_basin_vc_mo_ll_max[pvars_vc_mo_ll]   
    
    #PARAMETERS THAT VARY with veg_class, root_zone, lat, lon --> for these: take MAXIMUM instead of weighted sum (should correspond to VIC-global table)
    params_basin_vc_rz_ll = params_basin.copy()
    params_basin_vc_rz_ll['update_mask'] = np.ceil(params_basin_vc_rz_ll['fract_basin_area'])
    params_basin_vc_rz_ll = params_basin_vc_rz_ll[pvars_vc_rz_ll+['update_mask']]
    for dv in pvars_vc_rz_ll:
        params_basin_vc_rz_ll[dv] = params_basin_vc_rz_ll[dv]*params_basin_vc_rz_ll['update_mask']
    params_basin_vc_rz_ll_max = params_basin_vc_rz_ll.max(dim=('lat','lon'))
    params_basin_vc_rz_ll_max = params_basin_vc_rz_ll_max[pvars_vc_rz_ll]
          
    #Add in lat/lon back to the different dataframes
    lat_lon_xr = xr.Dataset(coords = dict(lat=('lat',[avg_lat]),lon=('lon',[avg_lon])))
    xr_list = [params_basin_vc_ll_sum,params_basin_sb_ll_sum,params_basin_nl_ll_sum,params_basin_vc_mo_ll_max,params_basin_vc_rz_ll_max]
    pvars_list = [pvars_vc_ll,pvars_sb_ll,pvars_nl_ll,pvars_vc_mo_ll,pvars_vc_rz_ll]
    dim_list = [dim_vc_ll,dim_sb_ll,dim_nl_ll,dim_vc_mo_ll,dim_vc_rz_ll]
    
    stor_final_xr = []
    for i in range(len(xr_list)):
        xri = xr_list[i].copy()
        xri['lat'] = lat_lon_xr['lat']
        xri['lon'] = lat_lon_xr['lon']
        dv_list = list(xri.data_vars)
        for dv in dv_list:
            xri[dv] = xri[dv].expand_dims(('lat','lon'))
            if len(dim_list[i]) == 1:
                xri[dv] = xri[dv].transpose(dim_list[i][0],'lat','lon')
            elif len(dim_list[i])==2:
                xri[dv] = xri[dv].transpose(dim_list[i][0],dim_list[i][1],'lat','lon')
        stor_final_xr.append(xri)

    #Now combine all of the xarrays together
    out_params = xr.combine_by_coords([params_basin_nl, params_basin_ll_combo]+stor_final_xr,
                                            data_vars='minimal')
    
    #update certain values 

    #set overstory - True (1) for 2,3,4,5,6,10
    out_params.sel(veg_class=1)['overstory'][:]= 0
    out_params.sel(veg_class=2)['overstory'][:] = 1
    out_params.sel(veg_class=3)['overstory'][:] = 1
    out_params.sel(veg_class=4)['overstory'][:] = 1
    out_params.sel(veg_class=5)['overstory'][:] = 1
    out_params.sel(veg_class=6)['overstory'][:] = 1
    out_params.sel(veg_class=7)['overstory'][:] = 0
    out_params.sel(veg_class=8)['overstory'][:] = 0
    out_params.sel(veg_class=9)['overstory'][:] = 0
    out_params.sel(veg_class=10)['overstory'][:] = 1
    out_params.sel(veg_class=11)['overstory'][:] = 0
    out_params.sel(veg_class=12)['overstory'][:] = 0
    out_params.sel(veg_class=13)['overstory'][:] = 0
    out_params.sel(veg_class=14)['overstory'][:] = 0
    out_params.sel(veg_class=15)['overstory'][:] = 0
    out_params.sel(veg_class=16)['overstory'][:] = 0
    out_params.sel(veg_class=17)['overstory'][:] = 0
    
    cv_vals = out_params['Cv'].values #clean up Nveg variable - make integer based on Cv
    ncv = len(cv_vals[cv_vals>0])
    out_params['Nveg'][:] = ncv
    
    #make sure certain variables are int32 (Nveg, gridcell, run_cell, fs_active, and overstory)
    int_vars = ['Nveg','gridcell','run_cell','fs_active','overstory']
    out_params[int_vars] = out_params[int_vars].astype('int32')
    
    #make sure mask is set to 1
    out_params['mask'][:] = 1
    out_params['mask'] = out_params['mask'].astype('int32')   
     
    #for open water (veg_class = 1), set albedo to 0.05
    out_params.sel(veg_class=1)['albedo'][:] = 0.05
    
    #for open water (veg_class = 1) and perennial snow and ice (veg_class = 16), set LAI and fcanopy to 0
    out_params.sel(veg_class=1)['LAI'][:] = 0
    out_params.sel(veg_class=1)['fcanopy'][:] = 0
    out_params.sel(veg_class=16)['LAI'][:] = 0
    out_params.sel(veg_class=16)['fcanopy'][:] = 0
    
    #for urban area - set root fractions to match VIC-global table
    out_params.sel(veg_class=14,root_zone=1)['root_fract'][:] = 0.44
    out_params.sel(veg_class=14,root_zone=2)['root_fract'][:] = 0.45
    out_params.sel(veg_class=14,root_zone=3)['root_fract'][:] = 0.11

    #make sure all root fracts sum to 1
    if 'root_fract' in out_params.data_vars:
        out_params['root_fract'] = out_params['root_fract'] / out_params['root_fract'].sum(dim = 'root_zone')
        
    return out_params
    
def create_domain_basin(basin_xr,orig_domain_file,avg_lon,avg_lat):
    """ """
    min_lon = basin_xr['lon'].values.min(); max_lon = basin_xr['lon'].values.max();
    min_lat = basin_xr['lat'].values.min(); max_lat = basin_xr['lat'].values.max();

    domain = xr.open_dataset(orig_domain_file)
    domain_basin = domain.sel(lat=slice(min_lat,min_lat),lon=slice(min_lon,min_lon)).load() #slice params file
    domain_basin = domain_basin.assign_coords(lat=np.atleast_1d(avg_lat))
    domain_basin = domain_basin.assign_coords(lon=np.atleast_1d(avg_lon))
    basin_area = basin_xr['basin_area_m2'].values; basin_area = basin_area[basin_area>0]; basin_area = basin_area[0] #remove any NaN values
    domain_basin['area'] = (('lat','lon'), np.expand_dims(np.expand_dims(basin_area,0),0))
    domain_basin['mask'] = (('lat','lon'), np.expand_dims(np.expand_dims(1,0),0)) #make sure mask is set to 1
    domain_basin['mask'] = domain_basin['mask'].astype('int32')
    return domain_basin
        
def create_forcings_basin(orig_forcings_file,basin_select,avg_lon,avg_lat):
    """ """
    #get lat/lon from params
    lat_lon_xr = xr.Dataset(coords = dict(lat=('lat',[avg_lat]),lon=('lon',[avg_lon])))

    #load in weather data and select basin
    wd = xr.open_dataset(orig_forcings_file).sel(basin=basin_select)

    wd['lat'] = lat_lon_xr['lat']
    wd['lon'] = lat_lon_xr['lon']

    forc_vars = list(wd.data_vars.keys())

    wd[forc_vars] = wd[forc_vars].expand_dims(('lat','lon'))
    wd[forc_vars] = wd[forc_vars].transpose('time','lat','lon')
    wd[forc_vars] = wd[forc_vars].astype('float32')

    wd = wd.drop_vars('basin')
    
    return wd