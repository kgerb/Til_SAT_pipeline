#!/bin/bash


SHARED_FOLDER=/data/02_input_SAT
OUTPUT_FOLDER=/data/03_output_SAT
SCRIPT_DIR=$(dirname "$0")

export SCRIPT_DIR

mkdir -p "$OUTPUT_FOLDER"


tiles=("$SHARED_FOLDER/*.las")
    num_tiles=${#tiles[@]}

if [ "$num_tiles" -eq 0 ]; then
    echo "No tiles found in $TILE_DIR. Exiting."
    exit 1
fi


bash "$SCRIPT_DIR/run_oracle_pipeline.sh"

unzip -o /data/03_output_SAT/*.zip -d /data/03_output_SAT/
rsync -avP /data/03_output_SAT/home/datascience/results/ /data/03_output_SAT/
rm -rf /data/03_output_SAT/home && rm -rf /data/03_output_SAT/*zip

echo "Segmentation complete. Results in $OUTPUT_FOLDER"