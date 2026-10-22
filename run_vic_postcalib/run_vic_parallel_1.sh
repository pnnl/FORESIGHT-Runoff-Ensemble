#!/bin/bash
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=12:00:00
#SBATCH --mem=64g
#SBATCH --job-name=test_vic_run
#SBATCH -o outfiles/%A.%a.out
#SBATCH -e errfiles/%A.%a.err
##SBATCH --mail-type=ALL
##SBATCH --mail-user=abigail.birnbaum@pnnl.gov

##select huc2 region
huc2reg='huc05'
scenname='ic0_fhist'

##set path to scratch
path_temp=/dev/shm/birn696
###path_temp=/gcfs/projects/foresight/hydrology/abirn_vic/run_vic_postcalib/stor_inputs

##paths to inputs
input_data_path=/gcfs/projects/foresight/hydrology/abirn_vic/input_data
path_domain=$input_data_path/domain_by_huc2/namerica_domain_${huc2reg}.nc
path_0625_fract=$input_data_path/grid_cell_conversions/grid_0625deg_basin/fract_cells_grid_0625_basin_${huc2reg}.csv

path_forcing_era5=/gcfs/projects/foresight/hydrology/ERA5/downscaled_era5_12km_by_basin/${huc2reg}
path_forcing_ace2=/gcfs/projects/foresight/hydrology/ACE2/ACE2_by_basin/${huc2reg}/${scenname}

##copy files over to temporary directory
rm -rf $path_temp
mkdir -p $path_temp
mkdir -p $path_temp/forcing
mkdir -p $path_temp/forcing/era5
mkdir -p $path_temp/forcing/ace2
mkdir -p $path_temp/forcing/ace2/${scenname}/
cp $path_domain $path_temp/
cp $path_0625_fract $path_temp/
cp $path_forcing_era5/*.nc $path_temp/forcing/era5/
cp -r $path_forcing_ace2/*.nc $path_temp/forcing/ace2/${scenname}/