#!/bin/bash

# Initialization script for the Til_SAT_pipeline
# checks for the provided arguments
# creates the folder structure
# copies the input file to the shared folder
# sets the necessary environment variables for the pipeline 

INPUT_FILE=$1
SUFFIX=$2
SHARED_FOLDER=$3

echo "=== SAT_DT_Pipeline Initialization ==="

# Validate inputs
if [ -z "$INPUT_FILE" ] || [ -z "$SHARED_FOLDER" ]; then
    echo "Usage: initialization.sh <input_file> <suffix> <shared_folder>"
    echo "Example: initialization.sh /path/to/file.las _processed /tmp/shared_data"
    exit 1
fi

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' does not exist!"
    exit 1
fi

# Create the shared folder path and export it
SHARED_FOLDER_PATH=$(realpath "$SHARED_FOLDER")
export SHARED_FOLDER_PATH

echo "Input file: $INPUT_FILE"
echo "Shared folder: $SHARED_FOLDER_PATH"

# get the basename without the suffix
BASENAME=$(basename "$INPUT_FILE" .las)
if [[ "$INPUT_FILE" == *.laz ]]; then
    BASENAME=$(basename "$INPUT_FILE" .laz)
fi
export BASENAME

# filename is with suffix
FILENAME=$(basename "${INPUT_FILE}")
export FILENAME

# Get the original file directory
ORIGINAL_DIR=$(dirname "$INPUT_FILE")
RESULTS_FOLDER_NAME="${PREFIX}_${BASENAME}_results"

export RESULTS_FOLDER_NAME
export ORIGINAL_DIR

# Create folder structure
echo "Creating folder structure..."
mkdir -p "${SHARED_FOLDER_PATH}/00_original"
mkdir -p "${SHARED_FOLDER_PATH}/01_subsampled"
mkdir -p "${SHARED_FOLDER_PATH}/02_input_SAT"
mkdir -p "${SHARED_FOLDER_PATH}/03_output_SAT"
mkdir -p "${SHARED_FOLDER_PATH}/04_merged"
mkdir -p "${SHARED_FOLDER_PATH}/05_detailview"
mkdir -p "${SHARED_FOLDER_PATH}/06_final_results"


# get the subsampled file names
SUBSAMPLED_5cm_FILE=${SHARED_FOLDER_PATH}/01_subsampled/${BASENAME}_subsampled_5cm.las
if [[ "$INPUT_FILE" == *.laz ]]; then
    SUBSAMPLED_5cm_FILE=${SHARED_FOLDER_PATH}/01_subsampled/${BASENAME}_subsampled_5cm.laz
fi

SUBSAMPLED_2cm_FILE=${SHARED_FOLDER_PATH}/01_subsampled/${BASENAME}_subsampled_2cm.las
if [[ "$INPUT_FILE" == *.laz ]]; then
    SUBSAMPLED_2cm_FILE=${SHARED_FOLDER_PATH}/01_subsampled/${BASENAME}_subsampled_2cm.laz
fi

export SUBSAMPLED_5cm_FILE
export SUBSAMPLED_2cm_FILE

# Copy the file to the shared folder
echo "Copying input file to shared folder..."
cp "$INPUT_FILE" "$SHARED_FOLDER_PATH/00_original/"
echo "✓ Copied $INPUT_FILE to $SHARED_FOLDER_PATH/00_original/"

echo "=== Initialization Complete ==="