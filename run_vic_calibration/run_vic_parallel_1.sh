#!/bin/bash
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=12:00:00
#SBATCH --mem=64g
#SBATCH --job-name=copy_inputs_to_temp
#SBATCH -o outfiles/%A.%a.out
#SBATCH -e errfiles/%A.%a.err
##SBATCH --mail-type=ALL
##SBATCH --mail-user=abigail.birnbaum@pnnl.gov

##select huc2 region
huc2reg='huc13'

##set path to scratch
##path_temp=/gcfs/projects/foresight/dev/shm/birn696
path_temp=/dev/shm/birn696

##paths to inputs
input_data_path=/gcfs/projects/foresight/hydrology/abirn_vic/input_data
path_params=$input_data_path/params_by_huc2/namerica_params_${huc2reg}.nc
path_domain=$input_data_path/domain_by_huc2/namerica_domain_${huc2reg}.nc
path_runoff=$input_data_path/calib_runoff_by_huc2/tf_runoff_${huc2reg}.nc
path_0625_fract=$input_data_path/grid_cell_conversions/grid_0625deg_basin/fract_cells_grid_0625_basin_${huc2reg}.csv
path_forcing=/gcfs/projects/foresight/hydrology/ERA5/downscaled_era5_12km_by_basin/${huc2reg}

##copy files over to temporary directory
rm -rf $path_temp
mkdir -p $path_temp
mkdir -p $path_temp/forcing
cp $path_params $path_temp/
cp $path_domain $path_temp/
cp $path_runoff $path_temp/
cp $path_0625_fract $path_temp/
cp $path_forcing/*.nc $path_temp/forcing/
