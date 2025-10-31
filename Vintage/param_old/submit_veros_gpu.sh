#!/bin/bash
#SBATCH -N 1
#SBATCH --ntasks-per-node=48
#SBATCH --time=00:10:00
#SBATCH --job-name=veros_gpu
#SBATCH --error=err.err
#SBATCH --output=out.out
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1

module load singularity/3.2.1

cd acc/
singularity exec ../veros.sif veros run acc.py
