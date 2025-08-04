#!/bin/bash
# limit memory
ulimit -v 188743680  # 200 GB in kilobytes (200 * 1024 * 1024)
# ------------------------------------------------
# NO NEED TO CHANGE #




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
INPUT_FILE_LOCAL=/data/00_original/$(basename $INPUT_FILE)
ORIGINAL_FILE_LOCAL=$INPUT_FILE_LOCAL


# Step 0: Subsampling the input point cloud to 2 cm and 5 cm and leave out all extra attributes
echo "[Step pre-processing...] Subsampling input file to 2cm and 10cm: $FILENAME ..." 
SUBSAMPLED_2cm_FILE=/data/01_subsampled/${BASENAME}_subsampled_2cm.las
if [[ "$INPUT_FILE" == *.laz ]]; then
    SUBSAMPLED_2cm_FILE=/data/01_subsampled/${BASENAME}_subsampled_2cm.las
fi

echo 
pdal translate /data/00_original/${FILENAME} ${SUBSAMPLED_2cm_FILE} --json="{ \"pipeline\": [ { \"type\": \"filters.voxelcentroidnearestneighbor\", \"cell\": 0.02 }]}" 

# subsample file for segmentanytree
SUBSAMPLED_10cm_FILE=/data/01_subsampled/$(basename $INPUT_FILE .las)_subsampled_10cm.las
if [[ "$INPUT_FILE" == *.laz ]]; then
    SUBSAMPLED_10cm_FILE=/data/01_subsampled/$(basename $INPUT_FILE .laz)_subsampled_10cm.las
fi

pdal translate ${SUBSAMPLED_2cm_FILE} ${SUBSAMPLED_10cm_FILE} --json="{ \"pipeline\": [ { \"type\": \"filters.voxelcentroidnearestneighbor\", \"cell\": 0.10 }]}" 
echo "step 0.5 finished" 
sleep 5

# Step 1: Tiling input file
echo "[Step 1] Tiling input file: $SUBSAMPLED_10cm_FILE ..." 

# Check if the subsampled 5 cm file is smaller than 3 GB - originally
if [ $(stat -c%s $SUBSAMPLED_10cm_FILE) -lt 3000000000 ]; then
    echo "Subsampled 5 cm file is smaller than 3 GB. Copying it to 02_input_SAT folder..." 
    rsync -avP $SUBSAMPLED_10cm_FILE /data/02_input_SAT/tiled_1.las
else
    pdal tile $SUBSAMPLED_10cm_FILE /data/02_input_SAT/tiled_#.las --length $TILE_SIZE --buffer $OVERLAP
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