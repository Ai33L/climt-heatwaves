#!/bin/bash
#SBATCH --ntasks-per-node=8
#SBATCH --time=01:00:00
#SBATCH --job-name=GKTL_traj
#SBATCH --partition=standard
#SBATCH --exclude=cn020,cn029,cn166,gpu002,cn001,cn005,cn097,gpu001,cn143,cn164,cn035,cn086,cn087,cn088,cn081,cn034,gpu027,cn080,cn028,gpu024,cn168,cn002,cn085,cn116,cn042,cn161,cn110,cn023,cn092,cn083,cn095,cn140,cn082,cn008
#SBATCH -N 1
##SBATCH --array=1-40
#SBATCH --qos=array-job

pass=0
while [ $pass -ne 1 ]
do

export LD_LIBRARY_PATH=/usr/lib64:$LD_LIBRARY_PATH
export LIBRARY_PATH=/usr/lib64:$LIBRARY_PATH
module load intel/2018.5.274
module load singularity/3.2.1
#module load iiser/apps/library/libseccomp/2.5.4

if singularity exec climt_rare.sif python GKTL_traj.py $2 $3 $1; then
pass=1
else
sleep 10
fi
done
~                                                                                                                                                                                                           
~                                                                                                                                                                                                           
~                                  
