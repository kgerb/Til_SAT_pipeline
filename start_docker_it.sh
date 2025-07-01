#!/bin/bash

docker run -it --rm --gpus device=1 \
  -v "$(pwd)":/workspace \
  -v /home/kg281/data/docker_til_sat:/data \
  til_sat
  
# source /opt/conda/etc/profile.d/conda.sh && conda activate base