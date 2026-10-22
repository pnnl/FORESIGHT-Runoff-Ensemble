#!/bin/bash
#SBATCH --partition=batch
##SBATCH --cpus-per-task=1
#SBATCH --nodes=1
##SBATCH --ntasks-per-node=1
#SBATCH --time=72:00:00
#SBATCH --mem=8g
#SBATCH --job-name=calib_vic_huc13
#SBATCH --array=0-59
#SBATCH -o outfiles/%A.%a.out
#SBATCH -e errfiles/%A.%a.err
##SBATCH --mail-type=ALL
##SBATCH --mail-user=abigail.birnbaum@pnnl.gov

module load mpi/openmpi-x86_64

eval "$(/opt/miniconda3/bin/conda shell.bash hook)"
conda activate foresight_vic

##python run_calibration_parallel.py $SLURM_ARRAY_TASK_ID

START_INDEX=$((SLURM_ARRAY_TASK_ID))
NUM_BASINS=$((3118))
NUM_JOBS=$((60))
TOTAL_LOOPS=$((NUM_BASINS/NUM_JOBS))

for i in $( eval echo {0..$TOTAL_LOOPS})
do
	TASK_ITEM=$((i*NUM_JOBS))
	TASK_ITEM=$((TASK_ITEM + START_INDEX))
	python run_calibration_parallel.py $TASK_ITEM
done	
	
conda deactivate
