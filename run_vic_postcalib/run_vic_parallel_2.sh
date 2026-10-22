#!/bin/bash
#SBATCH --partition=batch
##SBATCH --cpus-per-task=1
#SBATCH --nodes=1
##SBATCH --ntasks-per-node=1
#SBATCH --time=12:00:00
#SBATCH --mem=4g
#SBATCH --job-name=run_vic_postcalib
#SBATCH --array=0
#SBATCH -o outfiles/%A.%a.out
#SBATCH -e errfiles/%A.%a.err
##SBATCH --mail-type=ALL
##SBATCH --mail-user=abigail.birnbaum@pnnl.gov

module load mpi/openmpi-x86_64

eval "$(/opt/miniconda3/bin/conda shell.bash hook)"
conda activate foresight_vic

##python run_calibration_parallel.py $SLURM_ARRAY_TASK_ID

START_INDEX=$((SLURM_ARRAY_TASK_ID))
NUM_BASINS=$((1))
NUM_SCENARIOS=$((2))
NUM_JOBS=$((1))
TOTAL_LOOPS=$((NUM_BASINS*NUM_SCENARIOS/NUM_JOBS))

for i in $( eval echo {0..$TOTAL_LOOPS})
do
	TASK_ITEM=$((i*NUM_JOBS))
	TASK_ITEM=$((TASK_ITEM + START_INDEX))
	python run_vic_postcalib.py $TASK_ITEM
done	
	
conda deactivate
