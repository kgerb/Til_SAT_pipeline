# Tree Processing Pipeline

This pipeline processes point cloud data in `.las` and `.laz` format to perform various tasks such as tiling, tree instance segmentation and merging back to one single pointcloud. Below is an overview of the steps involved in the pipeline.

The model used for instance segmentation is [SegmentAnyTree](https://www.sciencedirect.com/science/article/pii/S0034425724003936).

## Steps Overview

1. **Subsampling the Input Point Cloud (Step 0.5)**
    - Subsamples the input point cloud to 2 cm (DetailView) and 10 cm (SegmentAnyTree)

2. **Tiling Input File (Step 1)**
    - Tiles the input file based on the specified tile size and overlap if the provided point cloud is > 3 GB.

3. **Tree Instance Segmentation (Step 2)**
    - Instance (individual trees) and semantic (Vegetation/Ground) segmentation.

4. **Merging Tiles & Remapping (Step 4)**
    - Merges the segmented tiles into a single file while trying to merge overlapping tree instances.
    - Remaps the points to the original resolution.

## How to run the pipeline
1. Clone the entire github repository including SegmentAnyTree. This fork is not synchronized with the actual repository and may represent an older state of the algorithm.

2. Make sure to have Docker installed on your system.

3. The models needx a large model file which can be pull via Github Large File Storage. Make sure it is set-up on your machine and pull it using `git lfs pull`.

4. To run the pipeline, follow the instructions:
   **File & Folder Setup**
   Requirements:
   ---- CHANGE EVERYTHING BELOW----
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
