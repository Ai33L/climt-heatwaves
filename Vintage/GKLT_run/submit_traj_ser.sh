#!/bin/bash
#SBATCH --ntasks-per-node=8
#SBATCH --time=00:10:00
#SBATCH --job-name=GKTL_traj
#SBATCH --partition=standard
#SBATCH -N 1
##SBATCH --array=1-40
#SBATCH --qos=array-job

cd /home/apps/DL-conda/bin
source activate
conda activate climt

cd /scratch/abel
python GKTL_traj.py $2 $3 $1          
~                                                                                                                                                                                                           
~                                                                                                                                                                                                           
~                                  
