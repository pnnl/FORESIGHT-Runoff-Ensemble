import os
import pandas as pd
import xarray as xr

#################### File that includes paths to constants for running VIC calibration ####################

reg_sel = 'huc06'

calib_start_year = 1982
calib_end_year = 2001
full_run_start_year = 1980
full_run_end_year = 2024

#paths to input and output
input_data_path = '/dev/shm/birn696/'
orig_params_file = input_data_path+'namerica_params_'+reg_sel+'.nc'
orig_domain_file = input_data_path+'namerica_domain_'+reg_sel+'.nc'
orig_runoff_file = input_data_path+'calib_qf_'+reg_sel+'.nc'

fract_cells_0625_file = input_data_path+'fract_cells_grid_0625_basin_'+reg_sel+'.csv'
orig_forcings_path = input_data_path+'forcing/downscaled_era5_12km_'+reg_sel+'_'

#where to save output
cur_path = '/gcfs/projects/foresight/hydrology/abirn_vic/run_vic_calibration/'
#general storage directories for VIC/calibration outputs that aren't basin specific
stor_vic_output_runoff = cur_path+'vic_output/vic_runoff_output/'+reg_sel+'/'
stor_vic_output_params = cur_path+'vic_output/vic_params_output/'+reg_sel+'/'
stor_calib_process = cur_path+'vic_output/calib_outfiles/'+reg_sel+'/'

#create storage directories that don't exist
#os.makedirs(stor_vic_output_runoff,exist_ok=True)
os.makedirs(stor_vic_output_params,exist_ok=True)
os.makedirs(stor_calib_process,exist_ok=True)
    
#working path - where to conduct calibration
working_path = input_data_path
 
#list of basins
basin_list = xr.open_dataset(orig_runoff_file)['basin'].values

# for calibration parameters (infilt, Dsmax, Ds, Ws, depth2, depth3, expt2, expt3)
plim_ctr = [[0.001, 0.8],  # infilt
            [1, 30],  # Dsmax: [1, 30], ['-20%', '20%']
            [0, 1],  # Ds
            [0.5, 1],  # Ws
            [0.1001, 2],  # depth2 - depth2 cannot be less than depth1 which is set to 0.1 m
            [0.1, 2],  # depth3
            [8, 30],  # expt2: [8, 30], ['-20%', '20%']
            [8, 30],]  # expt3: [8, 30], ['-20%', '20%']
                        
vic_config = '''\
# ######################################################################
# Simulation Parameters
# ######################################################################
MODEL_STEPS_PER_DAY   4  # number of model time steps in 24 hour period
SNOW_STEPS_PER_DAY    4  # number of snow model time steps in 24 hour period
RUNOFF_STEPS_PER_DAY  4  # number of runoff time steps in 24 hour period

STARTYEAR             {start_year} # year model simulation starts
STARTMONTH            1    # month model simulation starts
STARTDAY              1    # day model simulation starts
ENDYEAR               {end_year}
ENDMONTH              12
ENDDAY                31
CALENDAR              PROLEPTIC_GREGORIAN

FULL_ENERGY           FALSE # calculate full energy balance
FROZEN_SOIL           FALSE # calculate frozen soils

# ######################################################################
# DOMAIN INFO
# ######################################################################
DOMAIN ./vic_inputs/domain_{basin}.nc
DOMAIN_TYPE    LAT     lat
DOMAIN_TYPE    LON     lon
DOMAIN_TYPE    MASK    mask
DOMAIN_TYPE    AREA    area
DOMAIN_TYPE    FRAC    frac
DOMAIN_TYPE    YDIM    lat
DOMAIN_TYPE    XDIM    lon

#######################################################################
# State Files and Parameters
#######################################################################
#INIT_STATE ./vic_inputs/vic_state_{basin}.nc
#STATENAME  vic_state_{basin}
#STATEYEAR  {end_year}
#STATEMONTH 1
#STATEDAY   1
#STATESEC   0
#STATE_FORMAT NETCDF4

# ######################################################################
# Forcing Files and Parameters
# netcdf forcing files will be of the form: <FORCING1>YYYY.nc
# ######################################################################
FORCING1      ./vic_inputs/forcings_{basin}_
FORCE_TYPE    AIR_TEMP     T2      # Average air temperature, C
FORCE_TYPE    PREC         PRECIP  # Total precipitation (rain and snow), kg/m2/s
FORCE_TYPE    PRESSURE     PSFC    # Atmospheric pressure, Pa
FORCE_TYPE    SWDOWN       SWDOWN  # Incoming shortwave, W/m2
FORCE_TYPE    LWDOWN       GLW     # Incoming longwave radiation, W/m2
FORCE_TYPE    VP           VP      # Vapor pressure, kPa
FORCE_TYPE    WIND         WSPEED  # Wind speed, m/s

# ######################################################################
# Land Surface Files and Parameters
# ######################################################################
PARAMETERS          ./params_updated.nc
SNOW_BAND           FALSE
BASEFLOW            ARNO
JULY_TAVG_SUPPLIED  FALSE
LAI_SRC             FROM_VEGPARAM
ALB_SRC             FROM_VEGPARAM
FCAN_SRC            FROM_VEGPARAM
ORGANIC_FRACT       FALSE
NODES               3  # number of soil thermal nodes

# ######################################################################
# Output Files and Parameters
# ######################################################################
RESULT_DIR  ./
OUTFILE     vic_runoff
AGGFREQ     NDAYS   1  # Write output every 1 day
OUT_FORMAT  NETCDF4
OUTVAR      OUT_RUNOFF
'''


