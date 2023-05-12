#!/bin/bash
#SBATCH --ntasks-per-node=8
#SBATCH --time=01:00:00
#SBATCH --job-name=spinup
#SBATCH --error=err.err
#SBATCH --output=out.out
#SBATCH --partition=standard
#SBATCH -N 1


export LD_LIBRARY_PATH=/usr/lib64/libseccomp.so.2
module load intel/2018.5.274
module load singularity/3.2.1

singularity exec climt_rare.sif python spinup.py
