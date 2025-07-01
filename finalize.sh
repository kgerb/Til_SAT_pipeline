#!/bin/bash
# copy the csv with id, species, height
cp ${SHARED_FOLDER_PATH}/05_detailview/final_species_height.csv ${SHARED_FOLDER_PATH}/06_final_results/final_species_height.csv

# copy top down view of tree segemntation
cp ${SHARED_FOLDER_PATH}/04_merged/${BASENAME}_merged_top_view.png ${SHARED_FOLDER_PATH}/06_final_results/${BASENAME}_merged_top_view.png

# copy the prediction probabilities
cp ${SHARED_FOLDER_PATH}/05_detailview/species_classification/predictions_probs.csv ${SHARED_FOLDER_PATH}/06_final_results/prediction_probs.csv

# copy the folder with the final rresults to the folder where the original file is from
rsync -avP "${SHARED_FOLDER_PATH}/06_final_results/" "${ORIGINAL_DIR}/${RESULTS_FOLDER_NAME}/" --progress

rm -rf "${SHARED_FOLDER_PATH}"
