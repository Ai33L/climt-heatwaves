#!/bin/bash
#SBATCH --ntasks-per-node=8
#SBATCH --time=96:00:00
#SBATCH --job-name=spinup
#SBATCH --error=err.err
#SBATCH --output=out.out
#SBATCH --partition=standard
#SBATCH -N 1

cd /home/apps/DL-conda/bin
source activate
conda activate climt

cd /scratch/abel
python spinup.py
