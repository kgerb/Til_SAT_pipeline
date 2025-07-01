#!/bin/bash
# limit memory
ulimit -v 188743680  # 200 GB in kilobytes (200 * 1024 * 1024)
# ------------------------------------------------
# NO NEED TO CHANGE #








### the plan
# user defines input file -> must be stored in shared/00_original



# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <input_file> <output_suffix>"
    exit 1
fi



# Get the input file argument
INPUT_FILE=$1
OUTPUT_SUFFIX=$2
ORIGINAL_FILE=$INPUT_FILE
FILENAME=$(basename $INPUT_FILE)


#100 / 20
# tile size and overlap for tiling (depends on CRS of input data - maybe need to adjust)
# TILE_SIZE=100 # dont make it smaller than double the overlap
# OVERLAP=20 # some trees are 20 m wide, so this is the minimum overlap to detect them

# -------------------------------------------------
# NEED TO CHANGE #
# holds all temporary files and results thus satree_in, satree_out, single trees out, species out. will be deleted after pipeline!

# TMP_FOLDER="/mnt/ssd2/kg281/pipeline_results/tmp_pipeline_$(basename $INPUT_FILE .las)"
# if [[ "$INPUT_FILE" == *.laz ]]; then
#     TMP_FOLDER="/mnt/ssd2/kg281/pipeline_results/tmp_pipeline_$(basename $INPUT_FILE .laz)"
# fi


# # save basename in a variable
# BASENAME=$(basename $INPUT_FILE .las)
# if [[ "$INPUT_FILE" == *.laz ]]; then
#     BASENAME=$(basename $INPUT_FILE .laz)
# fi

# Limit CPU and GPU resources
CPU_CORES="0-40" # Limit CPU cores. DetailView (species classification) relies heavily on CPU, so the more the merrier!!
GPU_DEVICES="0" # Limit to GPU 0. it will always run on GPU 0. if you want to change this you need to change the predict.py inside DetailView and also in SegementAnyTree run_docker_locally.sh and here, too.

# # Define Conda environment names
# CONDA_ENV_OPEN3D="open3d_env_gpd" # this is for PDAL and Open3D
# CONDA_ENV_DETAILVIEW="detailview" # this is for DetailView (torch 2.4)

# no need to change anything below this line
# ------------------------------------------------

# # step 0: setup local folder structure
# mkdir -p $(dirname "$LOG_FILE")
# mkdir -p $TMP_FOLDER
# mkdir -p $TMP_FOLDER/00_original        # original point cloud (input)
# mkdir -p $TMP_FOLDER/01_subsampled      # subsampled point cloud (2 cm)
# mkdir -p $TMP_FOLDER/02_satree_in       # input for satree (downsampled to 5 cm)
# mkdir -p $TMP_FOLDER/02_satree_out      # output from satree (downsampled 5 cm version)
# mkdir -p $TMP_FOLDER/04_merged          # merged point cloud with tree instances (2 cm resolution)
# mkdir -p $TMP_FOLDER/05_detailview      # single trees with species classification (input for species classification)
# mkdir -p $TMP_FOLDER/07_species_merged  # final merged point cloud (2 cm) with tree instances and species classification
# mkdir -p $TMP_FOLDER/08_final_results   # final merged point cloud with tree instances and species classification

# copy the original file to the temporary folder keeping its base name
# looks like this for example: /mnt/data/mf1176/pipeline_results/tmp_pipeline_$(basename $INPUT_FILE .las)/00_original/$(basename $INPUT_FILE)
INPUT_FILE_LOCAL=/data/00_original/$(basename $INPUT_FILE)
ORIGINAL_FILE_LOCAL=$INPUT_FILE_LOCAL

# output directory for final data
# OUTPUT_DIRECTORY=$TMP_FOLDER/07_species_merged


# ----------------------------------------------
# start the pipeline
# first step is to copy the input file to the temporary folder
# then subsample it to 2 cm and 5 cm for the pipeline
# then tile it and run the tree detection
# then merge the tiles and extract the individual trees
# then run the species classification
# then merge the species classification with the tree instances
# then remap the attributes back to the original point cloud
# then copy the results to the final output folder
# then remove the temporary folder

echo "Starting pipeline..." 
# echo "Copying input file to temporary folder..." 
# if [ ! -f "$INPUT_FILE_LOCAL" ]; then
#     rsync -avP $INPUT_FILE $INPUT_FILE_LOCAL || { echo "Error: Failed to copy $INPUT_FILE. Host is down."; exit 1; } 
# fi


# Step 0: Subsampling the input point cloud to 2 cm and 5 cm and leave out all extra attributes
echo "[Step pre-processing...] Subsampling input file to 2cm and 5cm: $FILENAME ..." 
SUBSAMPLED_2cm_FILE=/data/01_subsampled/${BASENAME}_subsampled_2cm.las
if [[ "$INPUT_FILE" == *.laz ]]; then
    SUBSAMPLED_2cm_FILE=/data/01_subsampled/${BASENAME}_subsampled_2cm.las
fi

echo 
pdal translate /data/00_original/${FILENAME} ${SUBSAMPLED_2cm_FILE} --json="{ \"pipeline\": [ { \"type\": \"filters.voxelcentroidnearestneighbor\", \"cell\": 0.02 }
]
}" 

# subsample file for segmentanytree
SUBSAMPLED_5cm_FILE=/data/01_subsampled/$(basename $INPUT_FILE .las)_subsampled_5cm.las
if [[ "$INPUT_FILE" == *.laz ]]; then
    SUBSAMPLED_5cm_FILE=/data/01_subsampled/$(basename $INPUT_FILE .laz)_subsampled_5cm.las
fi

pdal translate ${SUBSAMPLED_2cm_FILE} ${SUBSAMPLED_5cm_FILE} --json="{ \"pipeline\": [ { \"type\": \"filters.voxelcentroidnearestneighbor\", \"cell\": 0.10 }
]
}" 
echo "step 0.5 finished" 
sleep 5

# Step 1: Tiling input file
echo "[Step 1] Tiling input file: $SUBSAMPLED_5cm_FILE ..." 

# Check if the subsampled 5 cm file is smaller than 3 GB - originally
if [ $(stat -c%s $SUBSAMPLED_5cm_FILE) -lt 3000 ]; then
    echo "Subsampled 5 cm file is smaller than 3 GB. Copying it to 02_input_SAT folder..." 
    rsync -avP $SUBSAMPLED_5cm_FILE /data/02_input_SAT/tiled_1.las
else
    pdal tile $SUBSAMPLED_5cm_FILE /data/02_input_SAT/tiled_#.las --length $TILE_SIZE --buffer $OVERLAP
    echo "step 1 finished" 
    sleep 5

    # sometimes the tiling still produces large files, so we need to tile them again. File is too large if it has more than 3 GB file size. then it should use half the tile size but same overlap. A tile smaller than 20x20m is not useful for the tree detection.
    # but not recursive as it is not necessary to tile the tiles again.
    # Step 1.5: Check if tiles are too large and tile them again
    echo "[Step 1.5] Checking if tiles are too large and tiling them again..." 
    index=1
    for f in /data/02_input_SAT/*.las; do
        if [ $(stat -c%s $f) -gt 2000000000 ]; then
            echo "Tile $f is too large. Tiling it again..." 
            pdal tile $f /data/02_input_SAT/tiled_again_${index}_#.las --length $((($TILE_SIZE*2) / 3)) --buffer $OVERLAP 
            # remove the old file
            rm -f $f 
            index=$((index + 1))
        fi
    done

### CHANGE BACK TO 1000 POINTS	
    echo "delete tiles with less than 1000 points to avoid empty point cloud error..." 
    for tile in /data/02_input_SAT/*.las; do
        point_count=$(pdal info --metadata $tile | grep '"count"' | sed 's/[^0-9]//g')
        echo "Tile $tile has $point_count points." 
        if [ "$point_count" -lt 1000 ]; then
            echo "Tile $tile has less than 1000 points. Deleting it..." 
            rm -f $tile
        fi
    done

    sleep 10
fi

conda deactivate
if [[ -z "$CONDA_DEFAULT_ENV" || "$CONDA_DEFAULT_ENV" == "base" ]]; then
    echo "No named Conda environment is active (or only base is active)."
else
    echo "Active Conda environment: $CONDA_DEFAULT_ENV"
fi


# check if only one tile is located inside 02_satree_in and if so, set a global variable to true, else false
# this is necessary for the following steps to know if there is only one tile to process
# if [ $(ls -1q /mnt/02_input_SAT | wc -l) -eq 1 ]; then
#     SINGLE_TILE=true
# else
#     SINGLE_TILE=false
# fi

