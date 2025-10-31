#!/bin/bash
#SBATCH --ntasks-per-node=8
#SBATCH --time=01:00:00
#SBATCH --job-name=GKTL_init
#SBATCH --partition=standard
#SBATCH --exclude=cn020,cn029,cn166,gpu002,cn001,cn005,cn097,gpu001,cn143,cn164,cn035,cn086,cn087,cn088,cn081,cn034,gpu027,cn080,cn028,gpu024,cn168,cn002,cn085,cn116
#SBATCH -N 1

pass=0
while [ $pass -ne 1 ]
do

export LD_LIBRARY_PATH=/usr/lib64:$LD_LIBRARY_PATH
export LIBRARY_PATH=/usr/lib64:$LIBRARY_PATH
module load intel/2018.5.274
module load singularity/3.2.1

if singularity exec climt_rare.sif python GKTL_init.py $1 $2 $3 $4; then
pass=1
else
sleep 10
fi
done
~                                                                                                                                                                                                           
~                                                                                                                                                                                                           
~                                                                                                                                                                                                           
~                                    
