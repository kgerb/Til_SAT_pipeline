#!/bin/bash

START_TIME=$(date +%s)

# define the overlap, Tile size is in meters (!) and should be at least twice the overlap
TILE_SIZE=100
OVERLAP=20

export TILE_SIZE
export OVERLAP


docker run -it --rm \
  --cpuset-cpus="0-49" \
  --memory=200g \
  --gpus device=1 \
  -v "$(pwd)":/workspace \
  -v /mnt/data/kg281/til_sat_benchmarking/test3:/data \
  -v /mnt/gsdata/projects/ecosense/UAV_clip:/mnt/original_file \
  til_sat \
  bash -c "bash main.sh /mnt/original_file/2024_05_10_L2_MID015_clippedtoinv2_xyzia_out-ds-subset100x100-25cm.laz test" #exec bash to keep the container running


END_TIME=$(date +%s)
ELAPSED_TIME=$((END_TIME - START_TIME))

echo "Process took $ELAPSED_TIME seconds." | tee /mnt/data/kg281/til_sat_benchmarking/test3/06_final_results/process_time.txt
# copy the provided file to the directory specieied and then...!

#  -v /mnt/gsdata/projects/ecosense/UAV_clip:/mnt/original_file \
