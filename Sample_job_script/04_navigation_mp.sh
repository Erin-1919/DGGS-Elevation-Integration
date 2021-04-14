#!/bin/bash
#SBATCH --array=1-100
#SBATCH --mem=0
#SBATCH --cpus-per-task=20
#SBATCH --time=24:00:00
#SBATCH --partition=cpu2019
#SBATCH --mail-user=your.email@ucalgary.ca
#SBATCH --mail-type=ALL

module load gcc/7.3.0
module load osgeo/gdal/3.0.2
module load osgeo/geos/3.8.0
module load osgeo/proj/6.2.1

export PATH=/home/mingke.li/R362/bin:$PATH
export LD_LIBRARY_PATH="/home/mingke.li/R362/lib64/R/lib:$LD_LIBRARY_PATH"
export PATH=/home/mingke.li/miniconda3/bin:$PATH

Rscript "06_dggs_navigation.R" 28
Rscript "06_dggs_navigation.R" 27
Rscript "06_dggs_navigation.R" 26

