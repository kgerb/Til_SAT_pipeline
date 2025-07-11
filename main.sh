#!/bin/bash

INPUT_FILE=$1
PREFIX=$2
SHARED_FOLDER=/data

# Run initialization script
source initialization.sh "$INPUT_FILE" "$PREFIX" "$SHARED_FOLDER"

# Create log file
LOG_FILE="${SHARED_FOLDER_PATH}/06_final_results/pipeline.log"

# Redirect all output to log file while still showing on screen
exec > >(tee -a "$LOG_FILE") 2>&1

RESOURCE_LOG="${SHARED_FOLDER_PATH}/06_final_results/resource_usage.log"

bash resource_logger.sh "$RESOURCE_LOG" 5 &
LOGGER_PID=$!


# Quick check
echo "=== Starting Docker Pipeline ==="
echo "Using variables:"
echo "  Shared folder: $SHARED_FOLDER_PATH"
echo "  File prefix: $FILENAME"
echo "  Tile size: $TILE_SIZE"
echo "  Overlap: $OVERLAP"
echo "Destination: $ORIGINAL_DIR/$RESULTS_FOLDER_NAME"


# Breakpoint - check variables and setup before proceeding
echo "=== BREAKPOINT ==="
echo "Press Enter to continue with Docker pipeline or Ctrl+C to exit"
# uncomment to have a breakpoint
# read -r 
echo "Starting Pipeline"


# Now let's call the individual scripts in the containers

######################## TILING ########################

# activate the conda env
source /opt/conda/etc/profile.d/conda.sh
conda activate tiling_env

bash /workspace/Tiling_Merge/tiling_main.sh $FILENAME $PREFIX

conda deactivate

####################### SEGMENTATION ########################

bash /workspace/SegmentAnyTree/run_SAT.sh


######################## MERGING ########################

source /opt/conda/etc/profile.d/conda.sh
conda activate tiling_env



python3 /workspace/Tiling_Merge/merge_tiles.py \
    --tile_folder /data/03_output_SAT \
    --original_point_cloud /data/01_subsampled/${BASENAME}_subsampled_5cm.las \
    --output_file /data/04_merged/${BASENAME}_merged.las

######################## REMAPPING TO ORIGINAL RESOLUTION ########################

python3 /workspace/Tiling_Merge/remapping_original_res.py \
    --original_file /data/00_original/${FILENAME} \
    --subsampled_file /data/04_merged/${BASENAME}_merged.las \
    --output_file /data/06_final_results/${BASENAME}_with_all_attributes_orig_res.las


######################## LAZ CONVERSION ########################

pdal translate \
    "/data/06_final_results/${BASENAME}_with_all_attributes_orig_res.las" \
    "/data/06_final_results/${BASENAME}_with_all_attributes_orig_res.laz" \
    --readers.las.use_eb_vlr=true \
    --writers.las.extra_dims="all"


kill $LOGGER_PID
