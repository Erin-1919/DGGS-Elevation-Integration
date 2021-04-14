#!/bin/bash
#SBATCH --array=1-100
#SBATCH --mem=80G
#SBATCH --cpus-per-task=16
#SBATCH --time=12:00:00
#SBATCH --mail-user=your.email@ucalgary.ca
#SBATCH --mail-type=ALL

module load gcc/7.3.0
module load osgeo/gdal/3.0.2
module load osgeo/geos/3.8.0
module load osgeo/proj/6.2.1

export PATH=/home/mingke.li/R362/bin:$PATH
export LD_LIBRARY_PATH="/home/mingke.li/R362/lib64/R/lib:$LD_LIBRARY_PATH"
export PATH=/home/mingke.li/miniconda3/bin:$PATH

python "05_dggs_modeling.py" 29
python "05_dggs_modeling.py" 28
python "05_dggs_modeling.py" 27

