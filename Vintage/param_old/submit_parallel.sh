#!/bin/bash
#SBATCH --job-name=sumbit_parallel
#SBATCH  -N 1
#SBATCH --ntasks-per-node=48
#SBATCH --error=err.err
#SBATCH --time=00:15:00
#SBATCH --output=out.out
#SBATCH --partition=standard
#SBATCH --array=0-10

echo "$SLURM_ARRAY_TASK_ID"
