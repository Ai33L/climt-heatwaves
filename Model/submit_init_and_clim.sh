#!/bin/bash
#SBATCH --ntasks-per-node=8
#SBATCH --time=96:00:00
#SBATCH --job-name=init_and_clim
#SBATCH --partition=standard
#SBATCH -N 1
#SBATCH --exclude=cn020,cn029,cn166,gpu002,cn001,cn005,cn097,gpu001,cn143,cn164,cn035,cn086,cn087,cn088,cn081,cn034,gpu027,cn080,cn028,gpu024,cn168,cn002,cn085,cn116,cn042,cn161,cn110,cn023,cn092,cn083,cn095,cn140,cn082,cn008
#SBATCH --array=1

export LD_LIBRARY_PATH=/usr/lib64/libseccomp.so.2
module load intel/2018.5.274
module load singularity/3.2.1
module load iiser/apps/library/libseccomp/2.5.4

singularity exec climt_rare.sif python init_and_clim.py "$SLURM_ARRAY_TASK_ID"