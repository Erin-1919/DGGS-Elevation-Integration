#!/bin/bash
#SBATCH --mem=40G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=5:0:0
#SBATCH --partition=cpu2019

#SBATCH --mail-user=your.email@ucalgary.ca
#SBATCH --mail-type=ALL

echo "Code starting at:"$(date) 
module load gcc/7.3.0 
module load osgeo/gdal/3.0.2 
module load osgeo/geos/3.8.0
module load osgeo/proj/6.2.1

export PATH=/home/mingke.li/miniconda3/bin:$PATH

python "01_data_acquisition.py" -80 43 -79.5 43.5 100 utm17
python "02_cdem_preprocess.py"
python "03_hrdem_preprocess.py"
