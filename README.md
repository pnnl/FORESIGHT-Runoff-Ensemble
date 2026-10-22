# Code to create a Basin-Scale Runoff Ensemble for CONUS, 1980-2024

Contact Abigail Birnbaum (abigail.birnbaum@pnnl.gov) with any questions

## Description
This document summarizes the procedure/scripts needed to set up and run basin-scale VIC simulations for CONUS and extensions into Mexico and Canada.

Due to the size of the files and the computational requirements of running VIC for 96,000+ basins, we recommend running this code on a high-performance computing machine.

This directory contains scripts used for pre-processing inputs, calibrating, and running the VIC hydrological model.

Some of the scripts include hardcoded data paths. Make sure to change these paths accordingly for your local machine/cluster.

This repository contains a requirements.txt file that lists the required Python packages for running the Python scripts.

### Scripts for pre-processing VIC inputs
This directory contains scripts used for pre-processing the inputs needed for running and calibrating VIC.

#### Step 1: Download input datasets
* Parameters/domain files from VIC-Global (Schaperow et al. 2021): https://zenodo.org/records/5038653 (data) and https://doi.org/10.1038/s41597-021-00999-4 (article)
* Forcings for calibration (downscaled ERA-5 from Tran et al. 2026): https://zenodo.org/records/22711782
* Forcings for ensemble (downscaled ACE2 from Tran et al. 2026): contact abigail.birnbaum@pnnl.gov
* USGS quick-flow dataset for calibration (): https://www.sciencebase.gov/catalog/item/5bc8aa93e4b0fc368ebfe165 (data) and https://doi.org/10.1016/j.jhydrol.2019.04.010 (article)
* GRFR runoff dataset for calibration (Yang et al. 2021): https://www.reachhydro.org/home/records/grfr
* Basin delineations (mosaic of HUC12 and MERIT basins) from Wood et al. 2026: https://zenodo.org/records/23483244

Place downloaded parameters, domain data in a new directory data/input_data/initial_input_data/
Put downloaded forcings data in data/forcings_data/era5d/ or data/forcings_data/ace2/
Put downloaded calibration data in data/input_data/calibration_target/ 

#### Step 2: Pre-process model parameters/domain files (/data_processing/preprocess_params_domain/)
* Step 2a: Get boundaries for each HUC-2/PFAF region and create shapefile for each HUC-2/PFAF region. Produces shapefiles and region_bounds.csv. (step2a_extract_region_bounds_shapefiles.ipynb)
* Step 2b: Filters parameters/domain files to just CONUS + Mexico/Canada regions of interest, created files are split by HUC-2/PFAF region. Script uses region_bounds.csv, na_params.nc, and na_domain.nc (since na_params.nc is so large, we did this on HPC cluster). (step2b_filter_params_domains_by_region.py).
* Step 2c: Calculate relationship between 1/16-degree grid cells (from VIC-Global) and basins (step2c_get_basin_fractions_0625deg.ipynb) and 12 km grid and basins (step2c_get_basin_fractions_12km.ipynb)

#### Step 3: Develop monthly calibration dataset (/data_processing/develop_calibration_target/)
Using both GRFR and USGS quickflow datasets an extended runoff calibration dataset for all basins in the modeling domain was created. The steps to creating this data are:
* Step 3a: Create the daily GRFR (step3a_runoff_mean_byHUC_parallel.R)
* Step 3b: Create summary data file for monthly runoff values for both GRFR and USGS quickflow (step3b_runoff_mean_byHUC_monthly.R and step3b_usgs_quickFlow_output_csv.R)
* Step 3c: Calculated correlation and monthly time series statistics for both GRFR and USGS quickflow datasets (step3c_monthly_analysis_parallel.R and step3c_create_summary_TS_monthly.R)
* Step 3d: Use the monthly summary time series information to find groups of watersheds. In this study all watersheds in a HUC02 were pooled together but one could develop subsets of groups based on clustering (step3d_grfr_watershed_clustering.R)
* Step 3e: Train random forest model on annual runoff totals using basins where both GRFR and USGS quickflow are available to then estimate the quickflow values for basins not included in the original USGS dataset. (step3e_randomForest_annual.R)
* Step 3f: Use monthly GRFR dataset to disaggregate the annual runoff values for the extended and original USGS quickflow datasets (step3f_annual_to_monthly_disaggregation.R)
* foresight_functions contains helper functions for step 3 tasks.
* The calibration target created using Step 3 is available at [DOI].

#### Step 4: Pre-process downscaled weather data (data_processing/preprocess_weather_forcings/)
* Step 4a-b: Split downscaled ERA5 weather data into files, split by HUC-2/PFAF region and year (step4a_split_era5d_by_huc2_year.py) and then aggregate by basin/6-hr time step (step4b_calculate_era5d_basin.py)
* Step 4c-d: Split downscaled ACE2 weather data into files, split by HUC-2/PFAF region and year (step4c_split_ace2_by_huc2_year.py) and then aggregate by basin (step4d_calculate_ace2_basin.py)   
   
#### Step 5: Calibration of VIC model (/run_vic_calibration/)
* Step 5a: Download and compile VIC model from https://github.com/UW-Hydro/VIC. We use version 5.1.
* Step 5b: Download and compile Ostrich https://doi-bor.github.io/ostrich/ (follow instructions from Guoqiang Tang here: https://github.com/NCAR/CTSM_calibration/blob/main/doc/install_ostrich). We use version 17.12.19
* Step 5c: Run calibration using run_calibration_parallel.py. For best results, run this script in parallel on HPC cluster. Calibrates each basin in specified HUC-2 region.
* Sample shell files for running script are provided (run_vic_parallel_1, run_vic_parallel_2, run_vic_parallel_3, and run_vic_parallel_outer). run_vic_parallel_outer shell script calls run_vic_parallel_1 (generates inputs for HUC-2 region), run_vic_parallel_2 (runs calibration), and run_vic_parallel_3 (deletes temporary files created during calibration process)
* vic_calibration_constants.py contains variables that must be specified prior to running calibration (e.g., HUC-2 region, points to correct params/domain/forcings/calibration target files and where to save output)
* calibration_methods.py contains helper methods used by run_vic_parallel.py
* run_vic.py is called by run_vic_parallel.py when using the Ostrich optimzer. Modify this script if you want to change the calibration function (currently set to KGE for monthly quick-flow).

#### Step 6: Run VIC for ACE2 ensemble members after calibration (/run_vic_postcalib/)
* We recommend generating the ensemble using HPC.
* run_vic_postcalib.py is Python script that runs VIC for specified ACE2 ensemble member and time period to run for.
* Sample shell scripts for running ensemble are provided (run_vic_parallel_1, run_vic_parallel_2, run_vic_parallel_3, and run_vic_parallel_outer). run_vic_parallel_outer shell script calls run_vic_parallel_1 (generates inputs for HUC-2 region), run_vic_parallel_2 (runs VIC for all basins in HUC-2 region for each forcing), and run_vic_parallel_3 (deletes temporary files created during VIC modeling process)
* vic_constants.py contain constants that must be specified before running run_vic_postcalib.py (e.g., time period to run for, which forcing dataset, which HUC-2 region)
* vic_helper_methods.py contains methods called by run_vic_postcalib.py

#### Step 7: Post-process output (/data_processing/postprocess_vic_output/)
* process_vic_output_parallel.py takes individual basin output and compiles into netCDF for all basins in specified HUC-2 region for all forcing datasets. Suggested to run script on HPC (sample shell script process_vic_output_parallel.sl provided)

#### Step 8: Generate paper figures (/generate_paper_figures/)
* generate_paper_figures.ipynb generates figures in associated manuscript using output produced from steps 1-7.
* calculate_daily_quantiles.py calculates quantiles (7q10-min and 5q10-max) used in paper_figures.ipynb.

## Authors and acknowledgment
Abigail Birnbaum; Jeremy Giovando; Youngjun Son; Cameron Bracken

## License
See license file.

## Project status
In active development.