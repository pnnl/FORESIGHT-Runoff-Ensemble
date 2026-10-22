#!/bin/bash
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=12:00:00
#SBATCH --mem=2g
#SBATCH --job-name=clear_temp_files
#SBATCH -o outfiles/%A.%a.out
#SBATCH -e errfiles/%A.%a.err
##SBATCH --mail-type=ALL
##SBATCH --mail-user=abigail.birnbaum@pnnl.gov

##path_temp=/gcfs/projects/foresight/dev/shm/birn696
path_temp=/dev/shm/birn696

##delete temporary directory
rm -rf $path_temp
