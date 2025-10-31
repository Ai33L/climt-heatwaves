#!/bin/bash
#SBATCH --ntasks-per-node=48
#SBATCH --time=00:10:00
#SBATCH --job-name=HELD
#SBATCH --error=err.err
#SBATCH --output=out.out
#SBATCH --partition=standard
#SBATCH -N 1

module load intel/2018.5.274
module load singularity/3.2.1

cd acc/
singularity exec ../veros.sif veros run acc.py
#mpirun -n 48 singularity exec CLIMT.sif python held_suarez.py
#mpirun -n 96 /home/arnab/ritu/software/gmx20194_plmd254_impi_dbl/bin/gmx_mpi_d mdrun -deffnm MD_ATP_onlywater_long3
