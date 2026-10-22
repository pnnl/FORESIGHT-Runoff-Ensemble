import os
from itertools import product
import pandas as pd

#################### File that includes paths to constants for running VIC calibration ####################

reg_sel = 'huc06'
full_run_start_year = 1980
full_run_end_year = 2024

#paths to input and output
input_data_path = '/dev/shm/birn696/'
orig_domain_file = input_data_path+'namerica_domain_'+reg_sel+'.nc'
fract_cells_0625_file = input_data_path+'fract_cells_grid_0625_basin_'+reg_sel+'.csv'

params_path = '/gcfs/projects/foresight/hydrology/abirn_vic/run_vic_calibration/vic_output/vic_params_output/'+reg_sel+'/'

#scenario_list = ['era5d','ic0_fhist','ic1_fhist','ic2_fhist','ic3_fhist','ic4_fhist','ic5_fhist','ic6_fhist','ic7_fhist','ic8_fhist','ic9_fhist']
scenario_list = ['era5d','ic0_fhist','ic1_fhist','ic2_fhist','ic3_fhist','ic4_fhist','ic5_fhist','ic6_fhist','ic7_fhist','ic8_fhist','ic9_fhist']

##list of basins
basin_list = os.listdir(params_path)
basin_list = [basin_list[i].split('_')[1] for i in range(len(basin_list))]

#basin-scenario permutations - list of length num basins * num scenarios
basin_scenario_pairs = list(product(basin_list, scenario_list))

#dictionary of forcings paths for each scenario
era5_dp = input_data_path+'forcing/era5/'
ace2_dp = input_data_path+'forcing/ace2/'+reg_sel+'/'
orig_forcings_dict = {
'era5d':era5_dp+'downscaled_era5_12km_'+reg_sel+'_',
'ic0_fhist':ace2_dp+'ic0_fhist/ACE2_noise_08_'+reg_sel+'_'+'ic0_fhist'+'_',
'ic1_fhist':ace2_dp+'ic1_fhist/ACE2_noise_08_'+reg_sel+'_'+'ic1_fhist'+'_',
'ic2_fhist':ace2_dp+'ic2_fhist/ACE2_noise_08_'+reg_sel+'_'+'ic2_fhist'+'_',
'ic3_fhist':ace2_dp+'ic3_fhist/ACE2_noise_08_'+reg_sel+'_'+'ic3_fhist'+'_',
'ic4_fhist':ace2_dp+'ic4_fhist/ACE2_noise_08_'+reg_sel+'_'+'ic4_fhist'+'_',
'ic5_fhist':ace2_dp+'ic5_fhist/ACE2_noise_08_'+reg_sel+'_'+'ic5_fhist'+'_',
'ic6_fhist':ace2_dp+'ic6_fhist/ACE2_noise_08_'+reg_sel+'_'+'ic6_fhist'+'_',
'ic7_fhist':ace2_dp+'ic7_fhist/ACE2_noise_08_'+reg_sel+'_'+'ic7_fhist'+'_',
'ic8_fhist':ace2_dp+'ic8_fhist/ACE2_noise_08_'+reg_sel+'_'+'ic8_fhist'+'_',
'ic9_fhist':ace2_dp+'ic9_fhist/ACE2_noise_08_'+reg_sel+'_'+'ic9_fhist'+'_',
}

#do we need to multiply precipitation? No for ERA5-D, yes for ACE2
multi_factor_dict = {
'era5d':1,
'ic0_fhist':6,'ic1_fhist':6,'ic2_fhist':6,'ic3_fhist':6,'ic4_fhist':6,
'ic5_fhist':6,'ic6_fhist':6,'ic7_fhist':6,'ic8_fhist':6,'ic9_fhist':6,}

#where to save output
cur_path = '/gcfs/projects/foresight/hydrology/abirn_vic/run_vic_postcalib/'
#general storage directories for VIC/calibration outputs that aren't basin specific
stor_vic_output_runoff = cur_path+'vic_output/'+reg_sel+'/'

#create storage directories that don't exist
os.makedirs(stor_vic_output_runoff,exist_ok=True)
    
#working path - where to conduct calibration
working_path = input_data_path
                         
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
FORCING1      ./vic_inputs/forcings_{basin}_{scenario}_
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
PARAMETERS          ./vic_inputs/params_{basin}_calib.nc
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
OUTVAR      OUT_BASEFLOW
OUTVAR      OUT_EVAP
OUTVAR      OUT_PET
OUTVAR      OUT_SOIL_MOIST
OUTVAR      OUT_SWE
'''


