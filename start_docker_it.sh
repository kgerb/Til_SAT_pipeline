#!/bin/bash

docker run -it --rm --gpus device=1 \
  -v "$(pwd)":/workspace \
  -v /data:/data \
  til_sat
  
# source /opt/conda/etc/profile.d/conda.sh && conda activate base