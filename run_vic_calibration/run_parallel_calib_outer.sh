#!/bin/bash
#SBATCH -o outfiles/%A.%a.out
#SBATCH -e errfiles/%A.%a.err

FIRSTJOBID=$(sbatch --parsable run_vic_parallel_1.sh)
SECONDJOBID=$(sbatch --parsable --dependency=afterok:$FIRSTJOBID run_vic_parallel_2.sh)
sbatch --parsable --dependency=afterany:$SECONDJOBID run_vic_parallel_3.sh