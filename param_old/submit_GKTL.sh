#!/bin/bash
#SBATCH --ntasks-per-node=8
#SBATCH --time=96:00:00
#SBATCH --job-name=GKTL_run
#SBATCH --error=err.err
#SBATCH --output=out.out
#SBATCH --partition=standard
#SBATCH -N 1
#SBATCH --array=1-25
#SBATCH --qos=array-job

export LD_LIBRARY_PATH=/usr/lib64:$LD_LIBRARY_PATH
export LIBRARY_PATH=/usr/lib64:$LIBRARY_PATH
module load intel/2018.5.274
module load singularity/3.2.1

rm -r k_10_1
singularity exec climt_rare.sif python GKTL_init.py 10 1
cd k_10_1

for i in {1..16}
do
singularity exec ../climt_rare.sif python ../GKTL_traj.py "$SLURM_ARRAY_TASK_ID" $i
if [ $i -ne 16 ]
    then
        singularity exec ../climt_rare.sif python ../GKTL_resampling.py $i
    fi
done

singularity exec ../climt_rare.sif python ../GKTL_wrap.py
~                                                                                                                                                                                                           
~                                                                                                                                                                                                           
~                                                                                                                                                                                                           
~                                    
