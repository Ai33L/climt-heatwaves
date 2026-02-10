#!/bin/bash
#SBATCH --ntasks-per-node=40
#SBATCH --time=96:00:00
#SBATCH --job-name=ID-ap
#BATCH --partition=cpu
#SBATCH -N 1
#SBATCH --exclude=cn007,gpu003

source /home/apps/DL-conda/bin/activate
conda activate xCDAT

cd /home/steveleonpadua/model-runs/aqua-planet/
python intensity-duration-master.py


