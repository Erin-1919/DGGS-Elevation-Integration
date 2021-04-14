#!/bin/bash
#SBATCH --mem=50G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=1:00:00
#SBATCH --partition=cpu2013,cpu2019
#SBATCH --mail-user=your.email@ucalgary.ca
#SBATCH --mail-type=ALL

module load gcc/7.3.0
module load osgeo/gdal/3.0.2
module load osgeo/geos/3.8.0
module load osgeo/proj/6.2.1

export PATH=/home/mingke.li/R362/bin:$PATH
export LD_LIBRARY_PATH="/home/mingke.li/R362/lib64/R/lib:$LD_LIBRARY_PATH"
export PATH=/home/mingke.li/miniconda3/bin:$PATH

R CMD Rserve --no-save
python "08_control_points.py"
