#!/bin/bash
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=12:00:00
#SBATCH --mem=64g
#SBATCH --array=0-2
#SBATCH --job-name=process_vic_output

eval "$(/opt/miniconda3/bin/conda shell.bash hook)"
conda activate foresight_vic

python process_vic_output_parallel.py $SLURM_ARRAY_TASK_ID

conda deactivate
