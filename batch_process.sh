#!/bin/bash

INPUT_DIR="/mnt/data/kg281/til_sat_benchmarking/TLS_3GB/"
# INPUT_DIR="/mnt/data/kg281/til_sat_benchmarking/test_benchmarking"

# INPUT_DIR="/mnt/data/kg281/til_sat_benchmarking/TLS_3GB/density"

for input_file in "$INPUT_DIR"/*; do
  if [ -f "$input_file" ]; then
    filename=$(basename -- "$input_file")
    extension="${filename##*.}"
    if [[ "$extension" != "laz" && "$extension" != "las" ]]; then
      echo "Skipping $filename: not a .laz file."
      continue
    fi

    name_no_ext="${filename%.*}"
    output_dir="$(dirname "$input_file")/${name_no_ext}_output"
    mkdir -p "$output_dir"

    # Set environment variables for tile size and overlap
    export TILE_SIZE=100
    export OVERLAP=20

    docker run -it --rm \
      --cpuset-cpus="0-49" \
      --memory=200g \
      --gpus device=1 \
      -v "$(pwd)":/workspace \
      -v "$output_dir":/data \
      -v "$INPUT_DIR":/mnt/original_file \
      til_sat \
      bash -c "bash main.sh /mnt/original_file/$filename test"
  fi
done