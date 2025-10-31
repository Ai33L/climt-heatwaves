#!/bin/bash
#SBATCH --ntasks-per-node=8
#SBATCH --time=96:00:00
#SBATCH --job-name=long_blob
#SBATCH --partition=standard
#SBATCH -N 1
#SBATCH --array=1-40
#SBATCH --qos=array-job

cd /home/apps/DL-conda/bin
source activate
conda activate climt

cd /scratch/abel
python long_run_blob.py "$SLURM_ARRAY_TASK_ID"
