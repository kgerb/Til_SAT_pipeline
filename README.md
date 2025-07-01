# Tree Processing Pipeline

This pipeline processes point cloud data in `.las` and `.laz` format to perform various tasks such as tiling, tree instance segmentation and species detection. Below is an overview of the steps involved in the pipeline.
It uses two existing AI models and combines them into a single workflow:

1) [SegmentAnyTree](https://www.sciencedirect.com/science/article/pii/S0034425724003936): This provides an instance segmentation to receive individual trees

2) [DetailView](https://besjournals.onlinelibrary.wiley.com/doi/10.1111/2041-210X.14503): This model iterates over the single trees and predicts tree species

## Steps Overview

1. **Subsampling the Input Point Cloud (Step 0.5)**
    - Subsamples the input point cloud to 2 cm (DetailView) and 10 cm (SegmentAnyTree)

2. **Tiling Input File (Step 1)**
    - Tiles the input file based on the specified tile size and overlap if the provided point cloud is > 3 GB.

3. **Tree Instance Segmentation (Step 2)**
    - Instance (individual trees) and semantic (Vegetation/Ground) segmentation.

4. **Merging Tiles (Step 4)**
    - Merges the segmented tiles into a single file while trying to merge overlapping tree instances.

5. **Species Detection (Step 5)**
    - Detects species of the individual trees.

6. **Merging Species Classification (Step 6)**
    - Merges the species classification results with the original point cloud.

7. **Remapping Attributes to Original Point Cloud (Step 7)**
    - Remaps attributes back to the full non-subsampled original point cloud (KDTree).

8. **Copy the resulting files back to storage**
    - The script copies the final results (only necessary files) to the NAS to the same directory as the individual input point cloud
    - Results folder on NAS will then look like this:
    ```
    - pipeline.log
    |    log file containing all output from the shell script
    |
    - prediction_probs.csv
    |    probabilities to the individual tree instances from DetailView
    |
    - final_species_height.csv
    |    tree heights & species of individual trees
    |
    - ...merged_top_view.png
    |    tree instance segmentation seen from top and colored by PredInstance. Good for a first visual impression if everything worked well, without loading the entire point cloud
    |
    - ...merged_with_species_species_distribution.png
    |    species distribution (i sometimes think there is an issue with how it calculates the percentage, this needs to be checked and verified again!)
    |
    - ...merged_final_top_view.png
    |    species top view, also good for a first impression
    |
    - ...merged_with_species.las
    |    subsampled 2 cm point cloud containing PredInstance, PredSemantic and species_id_x fields
    |
    - ..._with_all_attributes_orig_res.las
    |    original point cloud with all existing and additional fields
    |
    - ..._with_all_attributes_orig_res.laz
    |    compressed version for sharing with others
    ```

## How to run the pipeline
1. First make sure to clone the entire content of the github repository - also the two forks SegmentAnyTree and DetailView. They are not connected to the actual Github repositories and may represent an older state of the algorithm.

2. Make sure to have Docker installed on your system. When an older Docker version (<2.0) is used, Docker compose must be installed seperately. Check the installation with `docker compose version`. 

3. Both models need large model files and weights which can be pull via Github Large File Storage. Make sure it is set-up on your machine and pull it using `git lfs pull`.

4. To run the pipeline, follow the instructions:
   **File & Folder Setup**
   Requirements:
   1. As the files of different steps must be passed in between the docker containers, a shared folder must be defined which is the mounted to the docker containers.
   2. The filepath of the point cloud to be processed must the provided.
   3. A prefix for the project can be defined so the file can be differentiated.
    --> Setup when executing the script `bash run_docker_compose.sh <path_to_pointcloud> <prefix> <path_to_shared_folder>` **OR** define in the script itself.

  
   **System Setup**
   In `docker-compose.yml`, the manager of the indvidual containers, the available ressources are specified. Adapt to your system. 


   **Running the pipeline**
   ```
   cd <folder_containing_this_repository>
   bash run_docker_compose.sh # with files and folder defined within the script
   bash run_docker_compose.sh <path_to_pointcloud> <prefix> <path_to_shared_folder> # with files and folders provided in the command itself
   ```

    After copying the target point cloud to the shared folder, a prompt will display general information for review. Press **Enter** to confirm and proceed with the pipeline, or press **Ctrl+C** to cancel the operation.
   
   
## Notes and troubleshooting

- Adjust the paths and parameters according to your specific requirements as described above.
- I recall having issues with PDAL, so make sure to install `python-pdal` and not `pdal`.
- the two other repositories from DetailView and SegmentAnyTree are not forked here but put inside this repository, some things needed to change and i dont wanted to commit/push it everytime. And this way this is a working repository here.
- make sure to maybe have at the beginning a very small point cloud (50-100 MB) as an example for the pipeline to check if everything works without errors (especially the conda environments and the two AI submodules)
- there is a `lookup_german.csv` file inside this repository that holds the scientific names of the species and their german translation (was needed for teaching).
- Inside DetailView, there is also a lookup.csv file which is used for the species classification (same as the german version but without the german column)
- the script `run_pipeline.sh` might seem a bit chaotic, but this is due to the several steps and different in- and outputs needed for the two models. this could definetly be improved in the future
- also a config file or something similar might be a useful thing for the future to have all settings in only one location
